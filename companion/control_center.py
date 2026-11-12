"""Passport Music native Windows control center and notification-area icon."""
import argparse
import ctypes
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from background_music import own_root, install_root, request_stop, spawn, registered, run_command
from control_model import VERSION, atomic_json, read_json, installation_present, window_placement
from control_widgets import Button, Pages, card, BG
from control_brand import app_image, configure_windows_dpi
from control_service import (collect_status, restart_bridge, change_port, enable_startup, open_player,
                             install_package, monitor_work_areas, position_window, window_position)

TITLE = 'Passport Music · 音乐遥控器'
WHITE, INK, MUTED, RED, LINE = '#FFFFFF', '#191B1F', '#616876', '#E4002B', '#DFE2E7'


class Center:
    def __init__(self, directory, tray_only=False, installation_complete=False):
        self.directory = Path(directory)
        self.app = tk.Tk()
        self.app.withdraw()
        from PIL import ImageTk
        self.window_icon=ImageTk.PhotoImage(app_image(64),master=self.app)
        self.app.iconphoto(True,self.window_icon)
        self.app.title(TITLE)
        self.window_file=self.directory/'control-window-state.json'
        self.placement=window_placement(read_json(self.window_file),monitor_work_areas())
        self.app.geometry(f"{self.placement['width']}x{self.placement['height']}")
        self.app.minsize(min(1000,self.placement['width']),min(730,self.placement['height']))
        self.window_save=None
        self.placed=False
        self.app.configure(bg=BG)
        self.app.protocol('WM_DELETE_WINDOW', self.hide)
        self.app.bind('<Escape>', lambda _: self.hide())
        self.messages = queue.Queue()
        self.busy = False
        self.installing = False
        self.checking = False
        self.state = {}
        self.closing = False
        self.seen_open = time.time()
        self.tray = None
        self.installed = installation_present(self.directory,registered(),run_command(self.directory))
        self.make_style()
        self.make_window()
        self.make_tray()
        self.app.bind('<Configure>',self.window_changed,add='+')
        self.app.after(0,lambda:self.place_initial_window(tray_only))
        atomic_json(self.directory/'control-state.json', {'pid': os.getpid()})
        (self.directory/'control-close-request').unlink(missing_ok=True)
        self.app.after(100, self.poll)
        self.app.after(200, self.refresh)
        if installation_complete:self.app.after(700,self.installation_succeeded)

    def place_initial_window(self,tray_only):
        self.app.update_idletasks()
        position_window(self.app,self.placement['x'],self.placement['y'])
        self.placed=True
        if not tray_only:self.app.deiconify()

    def window_changed(self,event):
        if event.widget!=self.app or not self.placed or self.closing:return
        if self.window_save:self.app.after_cancel(self.window_save)
        self.window_save=self.app.after(700,self.save_window)

    def save_window(self):
        self.window_save=None
        if self.placed and self.app.state()=='normal':
            try:atomic_json(self.window_file,window_position(self.app))
            except OSError:pass

    def make_style(self):
        self.app.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(self.app)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10), background=WHITE, foreground=INK)
        style.configure('TFrame', background=WHITE)
        style.configure('TLabel', background=WHITE)
        style.configure('TButton', padding=(15, 9), borderwidth=1, relief='solid', background=WHITE)
        style.map('TButton', background=[('active', '#F7F7F8')])
        style.configure('Accent.TButton', background=RED, foreground=WHITE, borderwidth=0)
        style.map('Accent.TButton', background=[('active', '#BF0024'), ('disabled', '#E9A7B3')], foreground=[('disabled', WHITE)])
        style.configure('TNotebook', background=WHITE, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(24, 10), background='#F7F7F8')
        style.map('TNotebook.Tab', background=[('selected', WHITE)], foreground=[('selected', RED)])
        style.configure('TCheckbutton', background=WHITE)
        from PIL import Image, ImageDraw, ImageTk
        self.check_images=[]
        for selected in (False,True):
            image=Image.new('RGBA',(112,112),(255,255,255,0));draw=ImageDraw.Draw(image)
            draw.rounded_rectangle((8,8,104,104),radius=20,fill=RED if selected else WHITE,
                                   outline=RED if selected else '#A9ADB7',width=6)
            if selected:draw.line(((29,55),(48,74),(83,36)),fill='white',width=12,joint='curve')
            self.check_images.append(ImageTk.PhotoImage(image.resize((28,28),Image.Resampling.LANCZOS),master=self.app))
        style.element_create('MusicCheck.indicator','image',self.check_images[0],('selected',self.check_images[1]),width=34,sticky='w')
        style.layout('Music.TCheckbutton',[('Checkbutton.padding',{'sticky':'nswe','children':[
            ('MusicCheck.indicator',{'side':'left','sticky':'w'}),('Checkbutton.label',{'side':'left','sticky':'nswe'})]})])
        style.configure('Music.TCheckbutton',background=WHITE,font=('Microsoft YaHei UI',10),padding=(0,4))
        style.map('Music.TCheckbutton',background=[('active',WHITE)])

    def label(self, parent, text='', size=10, color=INK, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent.cget('background'), fg=color, anchor='w', justify='left',
                        font=('Microsoft YaHei UI', size, 'bold' if bold else 'normal'), **kw)

    def rule(self, parent):
        tk.Frame(parent, bg=LINE, height=1).pack(fill='x', pady=12)

    def make_window(self):
        sidebar=tk.Frame(self.app,bg='#F1F1F4',width=206);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        brand=tk.Frame(sidebar,bg='#F1F1F4');brand.pack(fill='x',padx=20,pady=(28,30))
        self.label(brand,'Passport',19,RED,True).pack(anchor='w')
        self.label(brand,'音乐遥控器',10,MUTED).pack(anchor='w',pady=(4,0))
        nav=tk.Frame(sidebar,bg='#F1F1F4');nav.pack(fill='x',padx=20)
        self.label(sidebar,'关闭窗口后继续在托盘运行',9,MUTED,wraplength=160).pack(side='bottom',padx=20,pady=24)
        body=tk.Frame(self.app,bg=BG);body.pack(side='left',fill='both',expand=True,padx=30,pady=26)
        head=tk.Frame(body,bg=BG);head.pack(fill='x',pady=(0,22))
        page_title=self.label(head,'连接状态',20,bold=True);page_title.pack(side='left')
        self.label(head,VERSION,9,MUTED).pack(side='right',pady=10)
        pages=tk.Frame(body,bg=BG);pages.pack(fill='both',expand=True)
        self.tabs=Pages(nav,pages,page_title)
        self.home=tk.Frame(pages,bg=BG);self.settings=tk.Frame(pages,bg=BG);self.help=tk.Frame(pages,bg=BG)
        for frame,name in ((self.home,'连接状态'),(self.settings,'设置'),(self.help,'使用帮助')):self.tabs.add(frame,text=name)

        summary=card(self.home)
        self.heading=self.label(summary,'正在检查连接…',18,bold=True);self.heading.pack(fill='x',pady=(0,8))
        self.detail=self.label(summary,'',10,MUTED,wraplength=680);self.detail.pack(fill='x')
        actions=tk.Frame(summary,bg=WHITE);actions.pack(fill='x',pady=(22,0))
        self.primary=Button(actions,text='打开网易云',primary=True,command=self.primary_action);self.primary.pack(side='left',padx=(0,12))
        self.connect_button=Button(actions,text='重新连接设备',command=self.reconnect);self.connect_button.pack(side='left')
        Button(actions,text='刷新状态',command=self.refresh).pack(side='right')
        status=card(self.home)
        self.label(status,'设备与音乐',12,bold=True).pack(fill='x',pady=(0,8))
        self.cards={}
        for i,(key,name,description) in enumerate((('device','Passport 设备','通过蓝牙连接电脑'),('music','网易云音乐','内部音量与播放进度'),('lyrics','歌词同步','跟随当前歌曲显示'))):
            if i:tk.Frame(status,bg='#F0F0F3',height=1).pack(fill='x',pady=12)
            row=tk.Frame(status,bg=WHITE);row.pack(fill='x')
            left=tk.Frame(row,bg=WHITE);left.pack(side='left')
            self.label(left,name,11).pack(anchor='w')
            self.label(left,description,9,MUTED).pack(anchor='w',pady=(3,0))
            self.cards[key]=self.label(row,'检查中',11,MUTED);self.cards[key].pack(side='right',padx=2)
        links=tk.Frame(self.home,bg=BG);links.pack(fill='x',pady=(0,8))
        Button(links,text='蓝牙设置',command=self.bluetooth).pack(side='left')
        self.activity=self.label(self.home,'',9,MUTED,wraplength=680);self.activity.pack(fill='x',pady=(2,0))

        startup=card(self.settings)
        self.label(startup,'启动与后台',13,bold=True).pack(fill='x',pady=(0,12))
        self.auto=tk.BooleanVar()
        self.auto_button=ttk.Checkbutton(startup,text='登录 Windows 后自动运行',variable=self.auto,command=self.toggle_startup,style='Music.TCheckbutton');self.auto_button.pack(anchor='w')
        self.label(startup,'启用后，后台异常退出也会自动恢复。',9,MUTED).pack(fill='x',pady=(6,14))
        row=tk.Frame(startup,bg=WHITE);row.pack(fill='x')
        self.install_button=Button(row,text='安装 / 更新后台',command=self.install);self.install_button.pack(side='right')
        self.install_status=self.label(startup,'',9,MUTED,wraplength=660)
        self.install_status.pack(fill='x',pady=(10,0))
        ports=card(self.settings)
        self.label(ports,'网易云控制端口',13,bold=True).pack(fill='x')
        self.label(ports,'通常不用修改。仅在端口被占用或被 Windows 保留时更换。',9,MUTED,wraplength=670).pack(fill='x',pady=(8,15))
        row=tk.Frame(ports,bg=WHITE);row.pack(fill='x')
        self.port=tk.StringVar(value='9223');self.port_dirty=False
        border=tk.Frame(row,bg='#DEDEE4',padx=1,pady=1);border.pack(side='left')
        self.port_input=tk.Entry(border,textvariable=self.port,width=10,bg='#FAFAFC',fg=INK,relief='flat',font=('Microsoft YaHei UI',11))
        self.port_input.pack(ipadx=10,ipady=8);self.port_input.bind('<KeyRelease>',lambda _:setattr(self,'port_dirty',True))
        Button(row,text='保存端口',command=self.save_port,primary=True).pack(side='left',padx=12)
        Button(row,text='复制启动参数',command=self.copy_args).pack(side='left')
        self.label(ports,'保存后重新打开网易云；原桌面和任务栏快捷方式也要使用相同端口。',9,MUTED,wraplength=675).pack(fill='x',pady=(12,0))
        more=card(self.settings,padding=20)
        row=tk.Frame(more,bg=WHITE);row.pack(fill='x')
        Button(row,text='诊断日志',command=lambda:self.folder('logs')).pack(side='left')
        Button(row,text='查看更新',command=lambda:webbrowser.open('https://github.com/wyh1351/passport-music/releases')).pack(side='right')

        for step,title,description,command,button in (
            ('01','启用后台','安装后可以在登录 Windows 时自动运行。',self.install,'安装 / 更新后台'),
            ('02','打开网易云','使用本软件打开网易云，再播放一首歌曲。',self.launch,'打开网易云'),
            ('03','配对 Passport','在 Windows 中添加 Passport Music，输入设备上的六位码。',self.bluetooth,'打开蓝牙设置')):
            item=card(self.help,padding=20)
            number=self.label(item,step,23,RED,True);number.pack(side='left',padx=(0,18),anchor='n')
            content=tk.Frame(item,bg=WHITE);content.pack(side='left',fill='x',expand=True)
            self.label(content,title,12,bold=True).pack(fill='x')
            self.label(content,description,9,MUTED,wraplength=560).pack(fill='x',pady=(6,12))
            Button(content,text=button,command=command).pack(anchor='w')

    def make_tray(self):
        import pystray
        icon=app_image(64)
        def post(fn):return lambda *_:self.messages.put(('call',fn))
        self.tray=pystray.Icon('PassportMusic',icon,'Passport Music',pystray.Menu(
            pystray.MenuItem('打开音乐遥控器',post(self.show),default=True),
            pystray.MenuItem('打开网易云',post(self.launch)),
            pystray.MenuItem('重新连接设备',post(self.reconnect)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('设置',post(lambda:self.show_tab(self.settings))),
            pystray.MenuItem('退出',post(self.exit)) ))
        self.tray.run_detached()

    def show(self):
        self.app.deiconify();self.app.lift();self.app.focus_force();self.refresh()

    def show_tab(self,frame):self.tabs.select(frame);self.show()

    def hide(self):
        if self.tray and self.tray.visible:self.app.withdraw()
        else:self.app.iconify()

    def worker(self, name, action, success=None):
        if self.busy:return
        self.busy=True;self.activity.configure(text=name)
        def run():
            try:result=action();self.messages.put(('done',(name,result,success)))
            except Exception as exc:self.messages.put(('error',str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def refresh(self):
        if not self.checking and not self.closing:
            self.checking=True
            def run():
                try:self.messages.put(('state',collect_status(self.directory)))
                except Exception:self.messages.put(('check_failed',None))
            threading.Thread(target=run,daemon=True).start()

    def poll(self):
        if self.closing:return
        while True:
            try:kind,value=self.messages.get_nowait()
            except queue.Empty:break
            if kind=='call':value()
            elif kind=='state':
                self.checking=False;self.state=value
                if not self.installed:
                    value.update(heading='开始使用音乐遥控器',detail='先启用后台，再打开网易云并配对 Passport。已有安装时会更新原目录，保留设置。',action='install')
                self.heading.configure(text=value['heading']);self.detail.configure(text=value['detail'])
                for key,label in self.cards.items():label.configure(text=value[key],fg=INK if value['ready'] else MUTED)
                primary_text={'install':'开始使用','start':'开始连接','settings':'修改端口','player':'重新打开网易云' if value.get('player',{}).get('process_running') else '打开网易云','bluetooth':'打开蓝牙设置','help':'刷新状态','none':'打开网易云'}[value['action']]
                self.primary.configure(text=primary_text)
                self.connect_button.configure(text='重新连接设备' if value['running'] else '开始连接')
                if not self.busy:self.auto.set(value['autostart'])
                self.auto_button.configure(state='normal' if self.installed else 'disabled')
                self.install_button.configure(text='正在重新安装…' if self.installing else '重新安装后台' if self.installed else '未安装后台',
                    state='normal' if self.installed and not self.installing else 'disabled')
                if not self.port_dirty and self.app.focus_get()!=self.port_input:self.port.set(str(value['port']))
                if self.tray:self.tray.title='Passport Music · '+value['heading'][:50]
            elif kind=='check_failed':
                self.checking=False;self.activity.configure(text='状态暂时无法读取，请点击刷新或查看诊断日志。')
            elif kind=='done':
                self.busy=False;name,result,success=value
                self.activity.configure(text='操作完成')
                if success:success(result)
                if self.closing:return
                self.refresh()
            elif kind=='error':
                self.busy=False;self.activity.configure(text='操作未完成')
                if self.installing:
                    self.installing=False
                    self.install_status.configure(text='安装未完成：'+value,fg='#B42318')
                messagebox.showerror('操作未完成',value,parent=self.app);self.refresh()
        request=read_json(self.directory/'control-open-request.json').get('at',0)
        if type(request) in (int,float) and request>self.seen_open:
            self.seen_open=request;self.show()
        if (self.directory/'control-close-request').exists():self.quit_ui();return
        self.app.after(250,self.poll)

    def heartbeat(self):
        self.refresh()
        if not self.closing:self.app.after(3000,self.heartbeat)

    def primary_action(self):
        action=self.state.get('action','player')
        {'install':self.install,'start':self.reconnect,'settings':lambda:self.show_tab(self.settings),'player':self.launch,
         'bluetooth':self.bluetooth,'help':self.refresh,'none':self.launch}[action]()

    def reconnect(self):self.worker('正在重新连接设备…',lambda:restart_bridge(self.directory))

    def launch(self):
        restart=bool(self.state.get('player',{}).get('process_running') and not self.state.get('player',{}).get('internal_player'))
        if restart and not messagebox.askokcancel('重新打开网易云','需要完全退出并重新打开网易云，才能启用遥控。当前播放会中断。是否继续？',parent=self.app):return
        self.worker('正在打开网易云…',lambda:open_player(self.directory,restart))

    def bluetooth(self):os.startfile('ms-settings:bluetooth')

    def folder(self,name):
        path=self.directory/name;path.mkdir(exist_ok=True);os.startfile(str(path))

    def toggle_startup(self):
        enabled=self.auto.get()
        self.worker('正在更新登录自启…',lambda:enable_startup(self.directory,enabled))

    def save_port(self):
        value=self.port.get()
        def saved(number):
            self.port_dirty=False
            messagebox.showinfo('端口已保存',f'控制端口：{number}\n请重新打开网易云；桌面和任务栏快捷方式也要使用相同端口。',parent=self.app)
        self.worker('正在保存端口并重连…',lambda:change_port(self.directory,value),saved)

    def copy_args(self):
        from control_model import port_number
        try:number=port_number(self.port.get())
        except ValueError as exc:messagebox.showerror('端口无效',str(exc),parent=self.app);return
        self.app.clipboard_clear();self.app.clipboard_append(f'--remote-debugging-port={number} --remote-debugging-address=127.0.0.1')
        self.activity.configure(text='启动参数已复制')
        messagebox.showinfo('已复制','在网易云快捷方式的“目标”末尾替换原遥控参数，保留原程序路径。',parent=self.app)

    def install(self):
        if self.busy:return
        self.installing=True
        self.install_button.configure(text='正在重新安装…' if self.installed else '正在安装…',state='disabled')
        self.install_status.configure(text='正在检查文件、重新安装并启动后台，请稍候…',fg=MUTED)
        def done(destination):
            self.installing=False
            if destination.resolve()!=self.directory.resolve():
                self.quit_ui()
                subprocess.Popen([str(destination/'PassportMusicControl.exe'),'--installation-complete'],cwd=destination,creationflags=subprocess.CREATE_NO_WINDOW)
            else:self.installation_succeeded()
        self.worker('正在安装后台…',lambda:install_package(self.directory),done)

    def installation_succeeded(self):
        self.installed=True
        self.install_status.configure(text='后台已安装并启动，设备会自动重新连接。',fg='#157347')
        messagebox.showinfo('后台安装完成','后台已安装并启动。\n设备会自动重新连接，原端口配置和配对已保留。',parent=self.app)
        self.refresh()

    def exit(self):
        self.worker('正在退出…',lambda:request_stop(self.directory),lambda _:self.quit_ui())

    def quit_ui(self):
        self.save_window()
        self.closing=True
        for callback in self.app.tk.splitlist(self.app.tk.call('after','info')):
            self.app.after_cancel(callback)
        if self.tray:self.tray.stop()
        state=read_json(self.directory/'control-state.json')
        if state.get('pid')==os.getpid():(self.directory/'control-state.json').unlink(missing_ok=True)
        self.app.destroy()

    def run(self):
        self.app.after(3000,self.heartbeat);self.app.mainloop()


def main():
    configure_windows_dpi()
    parser=argparse.ArgumentParser()
    parser.add_argument('--tray',action='store_true')
    parser.add_argument('--root',type=Path)
    parser.add_argument('--installation-complete',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    root=args.root.resolve() if args.root else own_root()
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p];api.CreateMutexW.restype=ctypes.c_void_p
    api.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=api.CreateMutexW(None,False,r'Local\FoloToy.PassportMusic.ControlCenter')
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    exists=ctypes.get_last_error()==183
    # During installation handover the old source window may still be exiting.
    # Wait for its mutex rather than silently losing the completion window.
    deadline=time.monotonic()+8
    while exists and args.installation_complete and time.monotonic()<deadline:
        api.CloseHandle(handle);time.sleep(.1)
        handle=api.CreateMutexW(None,False,r'Local\FoloToy.PassportMusic.ControlCenter')
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        exists=ctypes.get_last_error()==183
    try:
        if exists:
            if not args.tray:
                for directory in {root,install_root()}:
                    if directory.is_dir():atomic_json(directory/'control-open-request.json',{'at':time.time()})
            return
        Center(root,args.tray,args.installation_complete).run()
    finally:api.CloseHandle(handle)


if __name__=='__main__':main()

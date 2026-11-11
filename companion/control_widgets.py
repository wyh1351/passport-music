"""Small native Tk components for the music control center."""
import tkinter as tk
from tkinter import font

BG='#F7F7F8'
WHITE='#FFFFFF'
RED='#E4002B'
INK='#202127'
MUTED='#7B7E87'


def rounded(canvas, x, y, w, h, radius, **options):
    r=min(radius,w/2,h/2)
    points=(x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,
            x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y)
    return canvas.create_polygon(points,smooth=True,splinesteps=24,**options)


class Button(tk.Canvas):
    def __init__(self,parent,text,command=None,primary=False,nav=False,width=None):
        self.text=text;self.command=command;self.primary=primary;self.nav=nav
        self.selected=False;self.disabled=False;self.hover=False
        self.face=font.Font(family='Microsoft YaHei UI',size=10,weight='bold' if primary else 'normal')
        self.fixed_width=width
        super().__init__(parent,width=width or self.face.measure(text)+36,height=40,
                         bg=parent.cget('background'),highlightthickness=0,bd=0,takefocus=True,cursor='hand2')
        for event in ('<Configure>','<FocusIn>','<FocusOut>'):self.bind(event,lambda _:self.draw())
        self.bind('<Enter>',lambda _:self.set_hover(True));self.bind('<Leave>',lambda _:self.set_hover(False))
        self.bind('<ButtonRelease-1>',self.invoke);self.bind('<Return>',self.invoke);self.bind('<space>',self.invoke)

    def set_hover(self,value):self.hover=value;self.draw()

    def invoke(self,event=None):
        if self.disabled:return
        if event and event.type==tk.EventType.ButtonRelease and not (0<=event.x<self.winfo_width() and 0<=event.y<self.winfo_height()):return
        self.focus_set()
        if self.command:self.command()

    def configure(self,cnf=None,**kw):
        if cnf:kw.update(cnf)
        if 'text' in kw:
            self.text=kw.pop('text')
            if not self.fixed_width:super().configure(width=self.face.measure(self.text)+36)
        if 'state' in kw:self.disabled=kw.pop('state')=='disabled'
        if 'selected' in kw:self.selected=kw.pop('selected')
        if kw:super().configure(**kw)
        self.draw()

    config=configure

    def draw(self):
        self.delete('all');w=self.winfo_width();h=self.winfo_height()
        if w<2:return
        if self.nav:
            fill='#FDECEF' if self.selected else '#EEEEF1' if self.hover else self.cget('bg')
            color=RED if self.selected else INK;outline=fill;radius=10
        elif self.primary:
            fill='#EC9EAC' if self.disabled else '#C90026' if self.hover else RED
            color=WHITE;outline=fill;radius=20
        else:
            fill='#F2F2F5' if self.hover else WHITE;outline='#E4E4E9';color=MUTED if self.disabled else INK;radius=20
        rounded(self,1,1,w-2,h-2,radius,fill=fill,outline=outline,width=1)
        if self.focus_get()==self:rounded(self,3,3,w-6,h-6,radius-2,fill='',outline=RED,width=1)
        self.create_text(20 if self.nav else w/2,h/2,text=self.text,anchor='w' if self.nav else 'center',font=self.face,fill=color)


class Pages:
    def __init__(self,sidebar,body,title):self.sidebar=sidebar;self.body=body;self.title=title;self.entries=[]
    def add(self,frame,text):
        button=Button(self.sidebar,text,command=lambda:self.select(frame),nav=True,width=166)
        button.pack(fill='x',pady=4)
        self.entries.append((frame,button,text))
        if len(self.entries)==1:self.select(frame)
    def select(self,frame):
        for item,button,text in self.entries:
            if item==frame:
                item.pack(fill='both',expand=True);self.title.configure(text=text);button.configure(selected=True)
            else:item.pack_forget();button.configure(selected=False)


def card(parent,padding=24):
    """A real rounded surface, with the content sized by its requested height."""
    canvas=tk.Canvas(parent,bg=parent.cget('background'),highlightthickness=0,bd=0)
    canvas.pack(fill='x',pady=(0,16))
    content=tk.Frame(canvas,bg=WHITE)
    window=canvas.create_window(padding,padding,anchor='nw',window=content)
    def resize(_=None):
        width=canvas.winfo_width()
        canvas.itemconfigure(window,width=max(1,width-2*padding))
        height=content.winfo_reqheight()+padding*2
        canvas.configure(height=height)
        canvas.delete('surface')
        rounded(canvas,0,0,width,height,16,fill=WHITE,outline='',tags='surface')
        canvas.tag_lower('surface')
    canvas.bind('<Configure>',resize);content.bind('<Configure>',resize)
    return content

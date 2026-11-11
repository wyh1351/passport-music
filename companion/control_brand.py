"""Original Passport Music application mark, rendered at each native size."""
def app_image(size=64):
    from PIL import Image, ImageDraw
    scale=4
    image=Image.new('RGBA',(size*scale,size*scale),(0,0,0,0))
    draw=ImageDraw.Draw(image);unit=size*scale/64
    def rect(box,**kwargs):draw.rounded_rectangle(tuple(round(v*unit) for v in box),**kwargs)
    rect((2,2,62,62),radius=round(15*unit),fill='#E4002B')
    for x,height in ((18,18),(29,32),(40,24)):
        rect((x,32-height/2,x+6,32+height/2),radius=round(3*unit),fill='white')
    return image.resize((size,size),Image.Resampling.LANCZOS)


def configure_windows_dpi():
    import ctypes
    try:
        api=ctypes.WinDLL('user32',use_last_error=True)
        api.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
        api.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (OSError,AttributeError):
        try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError,AttributeError):pass
    try:ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('FoloToy.PassportMusic.ControlCenter')
    except (OSError,AttributeError):pass

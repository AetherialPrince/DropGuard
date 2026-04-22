import os, yaml
from views.theme import *
from tkinter import *
from tkinter import ttk, messagebox

CONFIG_FILE='config.yaml'
DEFAULT_FILE='config_default.yaml'
CHANGED=PANEL_ALT

META={
 'features.pcap':('Save Packet Captures','Write packet capture files to disk.'),
 'detection.portscan.threshold':('Ports Before Alert','Unique ports hit before port-scan alert.'),
 'detection.cooldown_seconds.PORT_SCAN':('Port Scan Cooldown','Seconds before repeating same alert.'),
 'sniffer.threads':('Worker Threads','Threads used for packet analysis.'),
 'pcap.interval':('Capture Interval','Seconds between capture file writes.'),
 'rules.NEW_HOST.alert':('Alert on New Device','Notify when a new device joins network.'),
 'rules.PORT_SCAN.blacklist':('Blacklist Scanner','Block IP after scan detection.'),
 'rules.PORT_SCAN.drop':('Drop Scanner Traffic','Drop packets from detected scanner.'),
 'rules.SSH.blacklist':('Blacklist SSH Source','Block suspicious SSH source.'),
 'rules.FTP.blacklist':('Blacklist FTP Source','Block suspicious FTP source.')
}

class Settings(Frame):
    def __init__(self,parent):
        super().__init__(parent,bg=BG)
        self.pack(fill='both',expand=True)
        self.vars={}; self.types={}; self.rows={}
        top=Frame(self,bg=BG); top.pack(fill='x',padx=10,pady=10)
        self.search=StringVar(); self.search.trace_add('write', lambda *_: self.render())
        Entry(top,textvariable=self.search,width=28).pack(side='left',padx=(0,8))
        Button(top,text='Save',command=self.save).pack(side='right',padx=4)
        Button(top,text='Reset',command=self.reset_visible).pack(side='right',padx=4)
        Button(top,text='Reload',command=self.load).pack(side='right',padx=4)
        self.canvas=Canvas(self,bg=BG,highlightthickness=0)
        self.scroll=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.body=Frame(self.canvas,bg=BG)
        self.body.bind('<Configure>', lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0),window=self.body,anchor='nw')
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.scroll.pack(side='right',fill='y')
        self.load()
    def read_yaml(self,p):
        if not os.path.exists(p): return {}
        with open(p,'r',encoding='utf-8') as f: return yaml.safe_load(f) or {}
    def write_yaml(self,p,d):
        with open(p,'w',encoding='utf-8') as f: yaml.safe_dump(d,f,sort_keys=False)
    def load(self):
        self.cfg=self.read_yaml(CONFIG_FILE); self.defaults=self.read_yaml(DEFAULT_FILE)
        self.vars.clear(); self.types.clear(); self.render()
    def render(self):
        for w in self.body.winfo_children(): w.destroy()
        self.build(self.body,self.cfg,'')
    def match(self,path):
        q=self.search.get().strip().lower()
        return not q or q in path.lower() or q in (META.get(path,('', ''))[0].lower())
    def branch_match(self,data,prefix=''):
        for k,v in data.items():
            path=f'{prefix}.{k}' if prefix else k
            if isinstance(v,dict):
                if self.branch_match(v,path): return True
            elif self.match(path): return True
        return False
    def build(self,parent,data,prefix):
        for k,v in data.items():
            path=f'{prefix}.{k}' if prefix else k
            if isinstance(v,dict):
                if not self.branch_match(v,path): continue
                lf=LabelFrame(parent,text=k.replace('_',' ').title(),bg=PANEL,fg=FG,padx=8,pady=8)
                lf.pack(fill='x',padx=8,pady=6)
                self.build(lf,v,path)
            else:
                if not self.match(path): continue
                row=Frame(parent,bg=PANEL)
                row.pack(fill='x',padx=10,pady=4)
                left=Frame(row,bg=PANEL); left.pack(side='left',fill='x',expand=True)
                name,desc=META.get(path,(k.replace('_',' ').title(),path))
                Label(left,text=name,bg=PANEL,fg=FG,font=('Segoe UI',10,'bold')).pack(anchor='w')
                Label(left,text=desc,bg=PANEL,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w')
                self.add_editor(row,path,v)
                self.paint_row(path)
    def add_editor(self,parent,path,val):
        self.types[path]=type(val)
        if isinstance(val,bool):
            var=BooleanVar(value=val)
            w=Checkbutton(parent,variable=var,bg=PANEL,activebackground=PANEL,selectcolor=PANEL_ALT,fg=FG,activeforeground=FG)
        else:
            var=StringVar(value=str(val))
            w=Entry(parent,textvariable=var,width=12,justify='center',bg=PANEL_ALT,fg=FG,insertbackground=FG,relief='flat')
        w.pack(side='right',padx=8)
        var.trace_add('write', lambda *_ ,p=path: self.paint_row(p))
        self.vars[path]=var
        self.rows[path]=parent
    def get_nested(self,data,path):
        cur=data
        for part in path.split('.'):
            if not isinstance(cur,dict): return None
            cur=cur.get(part)
        return cur
    def set_nested(self,data,path,val):
        cur=data; parts=path.split('.')
        for p in parts[:-1]: cur=cur.setdefault(p,{})
        cur[parts[-1]]=val
    def cast(self,path,val):
        t=self.types[path]
        if t is bool: return bool(val)
        if t is int: return int(val)
        if t is float: return float(val)
        return str(val)
    def paint_row(self,path):
        row=self.rows.get(path)
        if not row: return
        try: cur=self.cast(path,self.vars[path].get())
        except: cur=self.vars[path].get()
        default=self.get_nested(self.defaults,path)
        color=CHANGED if cur!=default else PANEL
        row.configure(bg=color)
        for child in row.winfo_children():
            try: child.configure(bg=color)
            except: pass
            for sub in getattr(child,'winfo_children',lambda:[])():
                try: sub.configure(bg=color)
                except: pass
    def save(self):
        data={}
        try:
            for p,var in self.vars.items(): self.set_nested(data,p,self.cast(p,var.get()))
            self.write_yaml(CONFIG_FILE,data)
            messagebox.showinfo('Saved','Settings saved.')
        except Exception as e:
            messagebox.showerror('Error',str(e))
    def reset_visible(self):
        for p,var in self.vars.items():
            d=self.get_nested(self.defaults,p)
            if d is not None: var.set(d)
        self.save(); self.load()
        messagebox.showinfo('Reset','Visible settings restored.')

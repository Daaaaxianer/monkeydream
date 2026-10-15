"""Create editable SVG teaching diagrams and matching local PNG previews."""
from pathlib import Path
from html import escape
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/uploads/rag-lesson-01'
PREVIEW = ROOT / '.tmp/rag-lesson-01'
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BOLD = Path('C:/Windows/Fonts/msyhbd.ttc')
INK, MUTED, ORANGE, TEAL = '#40372f', '#786e64', '#bf682a', '#357c78'
CREAM, PALE, GREEN, BORDER = '#fffcf8', '#faecdc', '#e9f3ef', '#e7dacc'


class Figure:
    def __init__(self, name, height, title, desc):
        self.name, self.height = name, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>']
        self.img = Image.new('RGB', (1920, height * 2), CREAM)
        self.draw = ImageDraw.Draw(self.img)
        self.rect(0, 0, 960, height, CREAM, CREAM, 0)
        self.text(40, 35, title, 34, bold=True)
        self.text(40, 89, desc, 22, MUTED)

    def rect(self, x, y, w, h, fill=PALE, stroke=BORDER, radius=15):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.draw.rounded_rectangle((x*2,y*2,(x+w)*2,(y+h)*2), radius=radius*2, fill=fill, outline=stroke, width=4)

    def text(self, x, y, text, size=26, color=INK, bold=False, center=False):
        font = ImageFont.truetype(str(BOLD if bold else FONT), size*2)
        width = self.draw.textlength(text, font=font)/2
        left = x-width/2 if center else x
        if left < 0 or left+width > 960:
            raise ValueError(f'Text outside canvas: {text}')
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{"middle" if center else "start"}" dominant-baseline="text-before-edge">{escape(text)}</text>')
        self.draw.text((left*2,y*2), text, font=font, fill=color, anchor='lt')

    def path(self, points, color=MUTED, arrow=False, dashed=False, width=3):
        seq=' '.join(f'{x},{y}' for x,y in points)
        dash=' stroke-dasharray="8 7"' if dashed else ''
        self.parts.append(f'<polyline points="{seq}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{dash}/>')
        if dashed:
            for a,b in zip(points,points[1:]):
                length=math.dist(a,b)
                for d in range(0,int(length),15):
                    p=[(a[i]+(b[i]-a[i])*t/length)*2 for t in (d,min(d+8,length)) for i in (0,1)]
                    self.draw.line(p,fill=color,width=width*2)
        else:
            self.draw.line([(x*2,y*2) for x,y in points],fill=color,width=width*2)
        if arrow:
            a,b=points[-2:]
            angle=math.atan2(b[1]-a[1],b[0]-a[0])
            pts=[b]+[(b[0]-13*math.cos(angle+t),b[1]-13*math.sin(angle+t)) for t in (-.45,.45)]
            self.parts.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="{color}"/>')
            self.draw.polygon([(x*2,y*2) for x,y in pts],fill=color)

    def dot(self,x,y,color,r=9):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')
        self.draw.ellipse(((x-r)*2,(y-r)*2,(x+r)*2,(y+r)*2),fill=color)

    def box(self,x,y,w,h,title,subtitle,fill=PALE):
        self.rect(x,y,w,h,fill)
        self.text(x+w/2,y+15,title,26,bold=True,center=True)
        self.text(x+w/2,y+57,subtitle,21,MUTED,center=True)

    def save(self):
        self.text(40,self.height-39,'MonkeyDream · RAG 第一课 · 概念示意',18,MUTED)
        OUT.mkdir(parents=True,exist_ok=True)
        PREVIEW.mkdir(parents=True,exist_ok=True)
        (OUT/f'{self.name}.svg').write_text(''.join(self.parts)+'</svg>',encoding='utf-8')
        self.img.save(PREVIEW/f'{self.name}.png')


def pipeline():
    f=Figure('pipeline',1240,'一次 RAG 回答，经历了什么？','先准备可检索的资料，再为每个问题挑选证据。')
    f.text(40,145,'01  建库 · 资料接入或更新时',27,ORANGE,True)
    for x,title,sub in [(40,'原始文档','PDF / Word / 网页'),(270,'解析文本','提取正文与结构'),(500,'切成 Chunk','保留局部语义'),(730,'Embedding','片段 → 向量')]:
        f.box(x,200,190,105,title,sub)
        if x<730: f.path([(x+190,252),(x+225,252)],ORANGE,True)
    f.path([(825,305),(825,330),(480,330),(480,353)],ORANGE,True)
    f.box(155,355,650,100,'知识库 / 索引','保存：片段原文 + 向量 + 来源元数据',GREEN)
    f.path([(40,492),(920,492)],BORDER,dashed=True)
    f.text(40,515,'02  问答 · 每次提问时',27,TEAL,True)
    for x,title,sub in [(40,'用户问题','保留原始问题'),(270,'问题编码','问题 → 向量'),(500,'Retriever','查询已有索引'),(730,'Top-K 片段','原文 + 来源')]:
        f.box(x,580,190,105,title,sub,GREEN)
        if x<730: f.path([(x+190,632),(x+225,632)],TEAL,True)
    f.path([(595,455),(595,576)],TEAL,True)
    f.text(612,468,'读索引',20,TEAL)
    f.path([(135,685),(135,735),(380,735),(380,785)],ORANGE,True)
    f.text(145,699,'原始问题',21,ORANGE)
    f.path([(825,685),(825,755),(580,755),(580,785)],TEAL,True)
    f.text(692,711,'检索资料',21,TEAL)
    f.box(80,790,800,100,'Prompt：问题 + 资料 + 回答要求','Augmentation · 增强本次上下文，不在此修改模型参数')
    f.path([(480,890),(480,924)],ORANGE,True)
    f.box(230,930,500,95,'LLM 阅读与生成','Generation · 根据提供的上下文组织答案',GREEN)
    f.path([(480,1025),(480,1059)],TEAL,True)
    f.box(230,1065,500,90,'答案 + 对应出处','回到原文检查证据是否支持论断')
    f.save()


def chunking():
    f=Figure('chunking',800,'为什么切块时要保留重叠？','示意参数：每块 100 tokens，相邻重叠 20 tokens。')
    f.text(40,150,'原文：关键句恰好跨过第 100 个 token',26,bold=True)
    f.rect(70,205,803,37,GREEN,GREEN,5)
    f.rect(361,199,47,49,'#e6b185','#bf682a',5)
    f.path([(378,187),(378,680)],ORANGE,dashed=True,width=2)
    f.text(70,252,'1',20,MUTED)
    f.text(407,252,'95–110：同一句话',21,ORANGE)
    f.text(845,252,'260',20,MUTED)
    for y,x,end,label in [(335,70,377,'Chunk 1 · tokens 1–100'),(460,318,625,'Chunk 2 · tokens 81–180'),(585,566,873,'Chunk 3 · tokens 161–260')]:
        f.text(x,y-39,label,23,bold=True)
        f.rect(x,y,end-x,51,PALE,ORANGE,8)
    f.rect(318,335,59,51,'#e6b185',ORANGE,8)
    f.rect(318,460,59,51,'#e6b185',ORANGE,8)
    f.rect(566,460,59,51,'#e6b185',ORANGE,8)
    f.rect(566,585,59,51,'#e6b185',ORANGE,8)
    f.path([(361,401),(408,401)],TEAL,width=5)
    f.text(424,383,'第二块完整包含关键句',24,TEAL,bold=True)
    f.text(40,691,'重叠减少边界信息丢失；仍应照顾句子、段落和表格结构。',24,MUTED)
    f.save()


def semantic():
    f=Figure('semantic-search',840,'从语义接近，到 Top-K 候选','文本与问题编码到兼容空间，再按检索分数排序。')
    f.rect(30,150,435,560,'#ffffff')
    f.rect(495,150,435,560,'#ffffff')
    f.text(55,173,'01  语义空间',26,TEAL,True)
    f.text(520,173,'02  选取 Top-3',26,ORANGE,True)
    f.path([(78,510),(425,510)],BORDER,True,width=2)
    f.path([(78,510),(78,245)],BORDER,True,width=2)
    for x,y,label,color in [(180,410,'A',TEAL),(260,440,'B',TEAL),(220,360,'Q',ORANGE),(383,280,'C',MUTED)]:
        f.dot(x,y,color,11)
        f.text(x+17,y-18,label,26,color,True)
    f.path([(220,360),(180,410)],TEAL,dashed=True,width=2)
    f.path([(220,360),(260,440)],TEAL,dashed=True,width=2)
    for y,label in [(545,'Q：RNA-seq 差异表达问题'),(588,'A / B：差异表达相关片段'),(631,'C：意大利面烹饪片段')]:
        f.text(55,y,label,23,MUTED)
    for i,(label,score) in enumerate([('Chunk 183','0.91'),('Chunk 29','0.87'),('Chunk 761','0.81'),('Chunk 91','0.53'),('Chunk 332','0.21')]):
        y=242+i*79
        f.rect(518,y,389,63,GREEN if i<3 else CREAM,GREEN if i<3 else BORDER,9)
        f.text(534,y+15,label,24,TEAL if i<3 else MUTED,i<3)
        f.text(819,y+15,score,24,TEAL if i<3 else MUTED,i<3)
    f.text(40,735,'点位与分数均为概念示意；相似分数不等于答案正确率。',24,MUTED)
    f.save()


def failures():
    f=Figure('failures',860,'RAG 答错时，先检查哪一步？','先看检索结果，再核对模型是否忠实地使用了证据。')
    for x,title,color in [(30,'检索失败',ORANGE),(495,'生成失败',TEAL)]:
        f.rect(x,150,435,545,'#ffffff')
        f.text(x+28,174,title,29,color,True)
    rows=[(246,'知识库中有正确证据','已获得充分且正确的证据'),(380,'未召回 / 排名过低','模型误读 / 遗漏条件'),(514,'输入上下文缺少答案','证据足够，答案仍然错误')]
    for y,left,right in rows:
        for x,label,color in [(50,left,ORANGE),(515,right,TEAL)]:
            f.rect(x,y,395,76,PALE if x==50 else GREEN)
            f.text(x+197,y+22,label,24,color,True,True)
            if y<514: f.path([(x+197,y+76),(x+197,y+124)],color,True)
    f.text(59,621,'先查：解析、切块、召回与过滤',23,ORANGE)
    f.text(524,621,'先查：提示、理解与生成过程',23,TEAL)
    f.text(40,725,'检索评价：有没有找到证据？  生成评价：有没有据此答对？',24,MUTED)
    f.text(40,767,'还要核对知识库质量；实际系统可能同时出现多种问题。',23,MUTED)
    f.save()


if __name__ == '__main__':
    pipeline()
    chunking()
    semantic()
    failures()
    print('Created four SVG diagrams and local PNG previews.')

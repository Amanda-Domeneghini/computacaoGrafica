import os
import sys
import json

if sys.platform.startswith("linux"):
    os.environ.setdefault("PYOPENGL_PLATFORM", "glx")

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

left = -500
right = 500
bottom = -500
top = 500
EPS = 1e-9 

# ESTRUTURAS
#ponto do usuário e polígonos
class Ponto:
    

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, outro):
        return Ponto(self.x + outro.x, self.y + outro.y)

    def __sub__(self, outro):
        return Ponto(self.x - outro.x, self.y - outro.y)

    def __mul__(self, escalar: float):
        return Ponto(self.x * escalar, self.y * escalar)

    def __repr__(self):
        return f"Ponto({self.x}, {self.y})"

#envelope aabb
class AABB:
    """Caixa alinhada aos eixos, descrita pelo centro e meias dimensoes."""

    def __init__(self, centro: Ponto, meio_tamanho: Ponto):
        self.centro = centro
        # meio_tamanho.x = meia largura; meio_tamanho.y = meia altura.
        self.meio_tamanho = meio_tamanho


#polígonos (aceita tanto côncavos quanto convexos)
class Poligono:
    def __init__(self, vertices: list[Ponto], cor):
        self.vertices = vertices
        self.cor = cor
        self.convexo = convexo(vertices)
        self._aabb_cache = self.calcula_aabb()

    def vertices_no_mundo(self) -> list[Ponto]:
        return self.vertices

    def calcula_aabb(self) -> AABB:
        vertices_mundo = self.vertices_no_mundo()
        all_x = [p.x for p in vertices_mundo]
        all_y = [p.y for p in vertices_mundo]

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        centro_x = (min_x + max_x) / 2.0
        centro_y = (min_y + max_y) / 2.0
        meio_x = (max_x - min_x) / 2.0
        meio_y = (max_y - min_y) / 2.0

        self._aabb_cache = AABB(Ponto(centro_x, centro_y), Ponto(meio_x, meio_y))
        return self._aabb_cache

#classe de grid linear para colisão
class Grid:
    def __init__(self, poligonos, n_colunas, n_linhas):
        self.n_colunas = n_colunas
        self.n_linhas = n_linhas
        self.largura_celula = (right - left) / n_colunas
        self.altura_celula = (top - bottom) / n_linhas
        # celulas[linha][coluna] = lista de INDICES de poligonos
        self.celulas = [[[] for _ in range(n_colunas)] for _ in range(n_linhas)]

        for i, t in enumerate(poligonos):
            aabb = t._aabb_cache
            c_min, l_min = self.celula_de(aabb.centro.x - aabb.meio_tamanho.x,
                                          aabb.centro.y - aabb.meio_tamanho.y)
            c_max, l_max = self.celula_de(aabb.centro.x + aabb.meio_tamanho.x,
                                          aabb.centro.y + aabb.meio_tamanho.y)
            for l in range(l_min, l_max + 1):
                for c in range(c_min, c_max + 1):
                    self.celulas[l][c].append(i)

    #Devolve (coluna, linha) da celula que contem (x, y), limitada ao grid
    def celula_de(self, x, y):
        c = int((x - left) / self.largura_celula)
        l = int((y - bottom) / self.altura_celula)
        c = max(0, min(self.n_colunas - 1, c))
        l = max(0, min(self.n_linhas - 1, l))
        return c, l

    def candidatos(self, p: Ponto) -> list[int]:
        if not (left <= p.x <= right and bottom <= p.y <= top):
            return []
        c, l = self.celula_de(p.x, p.y)
        return self.celulas[l][c]

    def desenha(self, p: Ponto):
        # celula que contem o ponto (preenchida, translucida)
        if left <= p.x <= right and bottom <= p.y <= top:
            c, l = self.celula_de(p.x, p.y)
            x0 = left + c * self.largura_celula
            y0 = bottom + l * self.altura_celula
            glColor4f(0.3, 0.6, 1.0, 0.25)
            glBegin(GL_QUADS)
            glVertex2f(x0, y0)
            glVertex2f(x0 + self.largura_celula, y0)
            glVertex2f(x0 + self.largura_celula, y0 + self.altura_celula)
            glVertex2f(x0, y0 + self.altura_celula)
            glEnd()

        # linhas do grid
        glColor3f(0.25, 0.25, 0.3)
        glLineWidth(1)
        glBegin(GL_LINES)
        for c in range(self.n_colunas + 1):
            x = left + c * self.largura_celula
            glVertex2f(x, bottom)
            glVertex2f(x, top)
        for l in range(self.n_linhas + 1):
            y = bottom + l * self.altura_celula
            glVertex2f(left, y)
            glVertex2f(right, y)
        glEnd()

#função identifica se plígono é convexo pois GL_POLYGON não desenha côncavos corretamente.
#Nesse caso, só a outline é utilizada
def convexo(vertices) -> bool:
    sinais = set()
    n = len(vertices)
    for k in range(n):
        a = vertices[k]
        b = vertices[(k + 1) % n]
        c = vertices[(k + 2) % n]
        cruz = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)
        if cruz > EPS:
            sinais.add(1)
        elif cruz < -EPS:
            sinais.add(-1)
    return len(sinais) <= 1

#lê os jsons de cenários
def carrega_cenario(caminho: str) -> list:
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    itens = dados["poligonos"] if "poligonos" in dados else dados["triangulos"]
    return [
        Poligono([Ponto(x, y) for x, y in item["vertices"]], tuple(item["cor"]))
        for item in itens
    ]


ponto_usuario = Ponto(0, 0)  # começa no centro
# Etapas ligadas/desligadas 
usar_subdivisao = True
usar_envelope = True

#FUNÇÕES DE COLISÃO
def ponto_na_aabb(a: AABB, p: Ponto) -> bool:
    return (abs(p.x - a.centro.x) <= a.meio_tamanho.x and
            abs(p.y - a.centro.y) <= a.meio_tamanho.y)

def ponto_sobre_segmento(p: Ponto, a: Ponto, b: Ponto) -> bool:
    """O ponto esta em cima do segmento a-b?"""
    # produto vetorial ~ 0 quer dizer "esta na mesma reta que a-b"
    cruz = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)
    if abs(cruz) > EPS:
        return False
    # e, estando na reta, precisa estar entre as pontas do segmento
    return (min(a.x, b.x) - EPS <= p.x <= max(a.x, b.x) + EPS and
            min(a.y, b.y) - EPS <= p.y <= max(a.y, b.y) + EPS)
 
#traça um linha e conta cruzamentos pare decidir se está dentro do polígono
def ponto_no_poligono(p: Ponto, vertices: list) -> bool:
    
    n = len(vertices)
 
    #ponto sobre uma aresta ou vertice conta como dentro
    for k in range(n):
        if ponto_sobre_segmento(p, vertices[k], vertices[(k + 1) % n]):
            return True
 
    #conta os cruzamentos do raio
    cruzamentos = 0
    for k in range(n):
        a = vertices[k]
        b = vertices[(k + 1) % n]
        
        if (a.y > p.y) != (b.y > p.y):
            x_cruz = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if x_cruz > p.x:  # cruzamento a direita do ponto
                cruzamentos += 1
    return cruzamentos % 2 == 1
 

#pipeline da aceleração dependendo das etapas ativadas
def consulta(p: Ponto) -> dict:
    
    if usar_subdivisao:
        indices = grid.candidatos(p)
    else:
        indices = list(range(len(poligonos)))
    apos_subdivisao = list(indices)

    if usar_envelope:
        indices = [i for i in indices
                   if ponto_na_aabb(poligonos[i]._aabb_cache, p)]
    apos_envelope = list(indices)

    # teste detalhado sempre roda
    contidos = [i for i in indices if ponto_no_poligono(p, poligonos[i].vertices)]

    return {
        "subdivisao": set(apos_subdivisao),
        "envelope": set(apos_envelope),
        "contidos": set(contidos),
        "testes_detalhados": len(apos_envelope),
    }
    

def desenha_ponto(ponto: Ponto, cor=(0.0, 1.0, 0.0)):
    glPointSize(8)
    glColor3f(*cor)
    glBegin(GL_POINTS)
    glVertex2f(ponto.x, ponto.y)
    glEnd()


def teclado_especial(tecla, x, y):
    global ponto_usuario
    passo = 10
    if tecla == GLUT_KEY_UP:
        ponto_usuario.y += passo
    elif tecla == GLUT_KEY_DOWN:
        ponto_usuario.y -= passo
    elif tecla == GLUT_KEY_LEFT:
        ponto_usuario.x -= passo
    elif tecla == GLUT_KEY_RIGHT:
        ponto_usuario.x += passo
    glutPostRedisplay()


def teclado(tecla, x, y):
    global usar_subdivisao, usar_envelope
    if tecla == b"1":
        usar_subdivisao = not usar_subdivisao
    elif tecla == b"2":
        usar_envelope = not usar_envelope
    print(f"subdivisao={usar_subdivisao}  envelope={usar_envelope}")
    glutPostRedisplay()



def desenha_aabb(aabb: AABB, cor=(0.15, 1.0, 0.15)):
    glColor3f(*cor)
    glLineWidth(2)
    glBegin(GL_LINE_LOOP)
    glVertex2f(aabb.centro.x + aabb.meio_tamanho.x, aabb.centro.y + aabb.meio_tamanho.y)
    glVertex2f(aabb.centro.x + aabb.meio_tamanho.x, aabb.centro.y - aabb.meio_tamanho.y)
    glVertex2f(aabb.centro.x - aabb.meio_tamanho.x, aabb.centro.y - aabb.meio_tamanho.y)
    glVertex2f(aabb.centro.x - aabb.meio_tamanho.x, aabb.centro.y + aabb.meio_tamanho.y)
    glEnd()


def desenha_poligono(poligono: Poligono):
    glColor3f(*poligono.cor)
    if poligono.convexo:
        # GL_POLYGON preenche direito so poligonos convexos
        glBegin(GL_POLYGON)
    else:
        #polígonos côncavos tem só o contorno
        glLineWidth(3)
        glBegin(GL_LINE_LOOP)
    for vertice in poligono.vertices_no_mundo():
        glVertex2f(vertice.x, vertice.y)
    glEnd()

    




def desenha():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(left, right, bottom, top)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glClearColor(0.05, 0.05, 0.07, 1)
    glClear(GL_COLOR_BUFFER_BIT)

    # só desenha a subdivisao se ela estiver ligada
    if usar_subdivisao:
        grid.desenha(ponto_usuario)

    res = consulta(ponto_usuario)

    for i, poligono in enumerate(poligonos):
        desenha_poligono(poligono)

        # só desenha envelopes se a etapa estiver ligada
        if usar_envelope and i in res["subdivisao"]:
            if i in res["envelope"]:
                cor = (1.0, 0.2, 0.2)    # vermelho: passou no envelope
            else:
                cor = (0.15, 1.0, 0.15)  # verde: barrado pelo envelope
            desenha_aabb(poligono._aabb_cache, cor)

    # o resultado do teste detalhado aparece na cor do ponto
    dentro = len(res["contidos"]) > 0
    cor_ponto = (1.0, 0, 0.0) if dentro else (0.0, 1.0, 0.0)
    desenha_ponto(ponto_usuario, cor_ponto)

    glutSwapBuffers()


def inicializa():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(left, right, bottom, top)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def main():
    global poligonos, grid

    caminho = sys.argv[1] if len(sys.argv) > 1 else "cenario_poligonos.json"
    poligonos = carrega_cenario(caminho)
    grid = Grid(poligonos, 10, 10)
    print(f"{len(poligonos)} poligonos carregados de {caminho}")

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(800, 800)
    glutInitWindowPosition(100, 100)

    glutCreateWindow(b"Trabalho 1")
    print(f"Utilize as setas para movimentar o ponto")
    print(f"Digite 1 para ativar/desativar grid e 2 para ativar/desativar envelopes")

    glutDisplayFunc(desenha)
    glutSpecialFunc(teclado_especial)  # captura setas
    glutKeyboardFunc(teclado)          # teclas 1 e 2: liga/desliga etapas
    inicializa()

    glutMainLoop()


if __name__ == "__main__":
    main()
import os
import sys

# Em alguns sistemas Linux, pode ser necessário comentar este bloco ou
# trocar "glx" pelo backend OpenGL disponível na máquina.
if sys.platform.startswith("linux"):
    os.environ.setdefault("PYOPENGL_PLATFORM", "glx")

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


class Ponto:
    """Representa um ponto (ou vetor) no plano."""

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


class AABB:
    """Caixa alinhada aos eixos, descrita pelo centro e meias dimensões."""
    def __init__(self, centro: Ponto, meio_tamanho: Ponto):
        self.centro = centro
        # x representa a meia largura; y representa a meia altura.
        self.meio_tamanho = meio_tamanho


class Poligono:
    """
    Polígono 2D com vértices armazenados em coordenadas locais (a partir do centro).
    O centro NÃO representa o centro geométrico do polígono ou da AABB, mas sim uma referência.
    Para obter um vértice no mundo, precisamos somar self.centro ao vértice.
    """

    def __init__(self, centro: Ponto, vertices: list[Ponto], cor):
        self.centro = centro
        self.vertices = vertices
        self.cor = cor

    def vertices_no_mundo(self) -> list[Ponto]:
        return [self.centro + vertice for vertice in self.vertices]

    def mover(self, deslocamento: Ponto) -> None:
        self.centro = self.centro + deslocamento

    def calcula_aabb(self) -> AABB:
        """Calcula e devolve a AABB deste polígono."""
        vertices = self.vertices_no_mundo()

        x_min = min(vertice.x for vertice in vertices)
        x_max = max(vertice.x for vertice in vertices)
        y_min = min(vertice.y for vertice in vertices)
        y_max = max(vertice.y for vertice in vertices)

        centro = Ponto((x_min + x_max) / 2, (y_min + y_max) / 2)
        meio_tamanho = Ponto((x_max - x_min) / 2, (y_max - y_min) / 2)

        return AABB(centro, meio_tamanho)


# Dois polígonos iniciais.
poligonos = [
    Poligono(
        centro=Ponto(-140, 30),
        vertices=[Ponto(-80, -50), Ponto(55, -65), Ponto(90, 20), Ponto(5, 85)],
        cor=(1.00, 0.65, 1.00),
    ),
    Poligono(
        centro=Ponto(130, -20),
        vertices=[Ponto(-70, -60), Ponto(75, -35), Ponto(45, 75), Ponto(-35, 95)],
        cor=(1.00, 0.45, 0.20),
    ),
]

poligono_selecionado = 0
deslocamento = 10

# Limites da câmera.
left = -500
right = 500
bottom = -500
top = 500


def aabbs_colidem(a: AABB, b: AABB) -> bool:
    """Informa se duas AABBs se sobrepõem."""
    distancia_x = abs(a.centro.x - b.centro.x)
    distancia_y = abs(a.centro.y - b.centro.y)

    sobrepoem_em_x = distancia_x <= a.meio_tamanho.x + b.meio_tamanho.x
    sobrepoem_em_y = distancia_y <= a.meio_tamanho.y + b.meio_tamanho.y

    return sobrepoem_em_x and sobrepoem_em_y


def desenha_eixos():
    glColor3f(0.45, 0.45, 0.45)
    glLineWidth(1)
    glBegin(GL_LINES)
    glVertex2f(left, 0)
    glVertex2f(right, 0)
    glVertex2f(0, bottom)
    glVertex2f(0, top)
    glEnd()


def desenha_poligono(poligono: Poligono):
    glColor3f(*poligono.cor)
    glBegin(GL_POLYGON)
    for vertice in poligono.vertices_no_mundo():
        glVertex2f(vertice.x, vertice.y)
    glEnd()

    # Marca o centro usado para posicionar o polígono.
    # Não confundir com o centro geométrico do polígono ou da AABB.
    glPointSize(6)
    glColor3f(1, 1, 1)
    glBegin(GL_POINTS)
    glVertex2f(poligono.centro.x, poligono.centro.y)
    glEnd()


def desenha_aabb(aabb: AABB, cor=(0.15, 1.0, 0.15)):
    """Desenha uma AABB somente com linhas."""
    x_min = aabb.centro.x - aabb.meio_tamanho.x
    x_max = aabb.centro.x + aabb.meio_tamanho.x
    y_min = aabb.centro.y - aabb.meio_tamanho.y
    y_max = aabb.centro.y + aabb.meio_tamanho.y

    glColor3f(*cor)
    glLineWidth(2)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x_min, y_min)
    glVertex2f(x_max, y_min)
    glVertex2f(x_max, y_max)
    glVertex2f(x_min, y_max)
    glEnd()


def desenha():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(left, right, bottom, top)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glClearColor(0.05, 0.05, 0.07, 1)
    glClear(GL_COLOR_BUFFER_BIT)

    desenha_eixos()

    for poligono in poligonos:
        desenha_poligono(poligono)

    # Calcula as AABBs dos dois polígonos.
    caixas = [poligono.calcula_aabb() for poligono in poligonos]

    # Se as duas AABBs forem válidas:
    if all(caixa is not None for caixa in caixas):
        # Testa a colisão
        colidem = aabbs_colidem(caixas[0], caixas[1])

        # Define a cor da AABB dependendo se houve colisão ou não.
        cor_caixa = (1.0, 0.15, 0.15) if colidem else (0.15, 1.0, 0.15)

        # Desenha as AABBs com a cor definida.
        for caixa in caixas:
            desenha_aabb(caixa, cor_caixa)

    # Destaca o centro do polígono selecionado.
    selecionado = poligonos[poligono_selecionado]
    glPointSize(11)
    glColor3f(0.2, 1.0, 0.2)
    glBegin(GL_POINTS)
    glVertex2f(selecionado.centro.x, selecionado.centro.y)
    glEnd()

    glutSwapBuffers()


def teclado(key: bytes, x: int, y: int):
    global poligono_selecionado

    if key == b"\x1b":  # ESC
        os._exit(0)
    elif key == b"1":
        poligono_selecionado = 0
    elif key == b"2":
        poligono_selecionado = 1

    glutPostRedisplay()


def teclas_especiais(key: int, x: int, y: int):
    """Move o polígono selecionado com as setas."""
    poligono_atual = poligonos[poligono_selecionado]

    if key == GLUT_KEY_LEFT:
        poligono_atual.mover(Ponto(-deslocamento, 0))
    elif key == GLUT_KEY_RIGHT:
        poligono_atual.mover(Ponto(deslocamento, 0))
    elif key == GLUT_KEY_UP:
        poligono_atual.mover(Ponto(0, deslocamento))
    elif key == GLUT_KEY_DOWN:
        poligono_atual.mover(Ponto(0, -deslocamento))

    glutPostRedisplay()


def inicializa():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(left, right, bottom, top)
    glMatrixMode(GL_MODELVIEW)


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(800, 800)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Gabarito: colisao somente por AABB")

    glutDisplayFunc(desenha)
    glutKeyboardFunc(teclado)
    glutSpecialFunc(teclas_especiais)

    inicializa()

    print("Controles: 1/2 para selecionar um poligono; setas para mover; ESC para sair.")
    print("AABB verde: livre; AABB vermelha: colisao.")
    glutMainLoop()


if __name__ == "__main__":
    main()

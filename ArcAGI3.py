"""
Agente para ARC-AGI-3 — resuelve el nivel 1 del juego público "ls20".

ls20 no da instrucciones explícitas: el avatar se mueve por una rejilla
llevando una "llave" y gana al llegar a una puerta cuya forma coincida
con la de la llave (hay baldosas "rotadoras" que cambian la forma de la
llave al pisarlas). Como no se conocen de antemano el mapa ni las reglas
exactas del nivel, este agente no intenta adivinar una secuencia fija de
movimientos: explora el árbol de acciones por amplitud (BFS), reiniciando
y reproduciendo la secuencia conocida cada vez que quiere probar una rama
nueva. Al ser el nivel 1 el tutorial (mecánicas mínimas), el espacio de
estados debería ser pequeño y encontrar la salida es factible con este
enfoque de fuerza bruta guiada.

Nota: esto prioriza RESOLVER el nivel (llegar a WIN) por encima de
la eficiencia en número de acciones (la métrica RHAE de ARC-AGI-3).
Para maximizar puntaje haría falta un agente que además aprenda el
modelo del juego (qué baldosa es rotadora, qué forma abre qué puerta)
en vez de explorar a ciegas.

------------------------------------------------------------------
INSTALACIÓN Y USO
------------------------------------------------------------------
1) Requiere Python >= 3.12

   pip install arc-agi-3

2) Consigue una API key en https://three.arcprize.org/ y expórtala:

   export ARC_API_KEY="tu-api-key-aqui"

3) Ejecuta este archivo:

   python ls20_level1_solver.py
------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import json
from collections import deque

from arc_agi_3 import Agent, Swarm
from arc_agi_3._structs import FrameData, GameAction, GameState


def frame_hash(frame: FrameData) -> str:
    """Huella única del tablero actual, para no repetir estados ya vistos."""
    return hashlib.md5(json.dumps(frame.frame).encode()).hexdigest()


class Ls20Level1Solver(Agent):
    # Margen generoso: cada "nodo" de la búsqueda cuesta un RESET +
    # reproducir la secuencia conocida + 1 movimiento nuevo.
    MAX_ACTIONS = 3000

    # Profundidad máxima de la búsqueda. El nivel 1 es el tutorial,
    # así que no debería hacer falta mucho más que esto. Súbelo si
    # el agente se queda sin secuencias por probar y no ha ganado.
    MAX_DEPTH = 20

    # Movimientos simples a explorar (excluye RESET y ACTION6, que
    # necesita coordenadas x,y de clic).
    MOVES = [
        GameAction.ACTION1,  # arriba
        GameAction.ACTION2,  # abajo
        GameAction.ACTION3,  # izquierda
        GameAction.ACTION4,  # derecha
        GameAction.ACTION5,  # interactuar / usar en la baldosa actual
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue: deque[list[GameAction]] = deque([[]])  # secuencias por probar (BFS)
        self.current_seq: list[GameAction] = []
        self.replay_pos = 0
        self.visited: set[str] = set()

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def _next_branch(self) -> GameAction:
        """Descarta la rama actual y arranca la siguiente secuencia de la cola."""
        self.current_seq = self.queue.popleft() if self.queue else []
        self.replay_pos = 0
        action = GameAction.RESET
        action.reasoning = "Probando la siguiente secuencia de la cola (BFS)"
        return action

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        # Arranque de un episodio nuevo: cargar la próxima secuencia a probar.
        if latest_frame.state is GameState.NOT_PLAYED:
            return self._next_branch()

        # Esta rama terminó mal: descartarla y seguir con la siguiente.
        if latest_frame.state is GameState.GAME_OVER:
            return self._next_branch()

        # ¿Aún estamos reproduciendo pasos ya conocidos de esta secuencia?
        if self.replay_pos < len(self.current_seq):
            move = self.current_seq[self.replay_pos]
            self.replay_pos += 1
            move.reasoning = f"Reproduciendo paso {self.replay_pos}/{len(self.current_seq)} conocido"
            return move

        # Llegamos al final de la secuencia conocida: nodo nuevo del árbol.
        # Si no lo hemos visto, registramos el tablero y encolamos sus hijos.
        h = frame_hash(latest_frame)
        if h not in self.visited and len(self.current_seq) < self.MAX_DEPTH:
            self.visited.add(h)
            for m in self.MOVES:
                if m in latest_frame.available_actions:
                    self.queue.append(self.current_seq + [m])

        # Este nodo ya se exploró (o llegamos al límite de profundidad):
        # pasar a la siguiente rama pendiente.
        return self._next_branch()


if __name__ == "__main__":
    swarm = Swarm(
        agent=Ls20Level1Solver,
        ROOT_URL="https://three.arcprize.org",
        games=["ls20"],
        tags=["ls20-level1-bfs-solver"],
    )
    scorecard = swarm.main()
    print(f"Puntaje final: {scorecard.score}")

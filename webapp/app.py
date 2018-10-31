import sys
import qutip as qt
from magic import *
import random

import json
import socketio
import eventlet
import eventlet.wsgi
from flask import Flask, request, Response, render_template

def upgrade_tensor(op, i, n, discretization=2):
    return qt.tensor(*[qt.identity(discretization)]*(i),\
                       op,\
                     *[qt.identity(discretization)]*(n-i-1))

class Game:
    def __init__(self, players):
        self.n_players = players
        self.unitary = qt.rand_unitary(2**self.n_players)
        #self.unitary = (-2*math.pi*1j*0.001*qt.rand_herm(2**self.n_players)).expm()
        self.current_players = []
        self.player_colors = [[random.uniform(0,1), random.uniform(0,1), random.uniform(0,1)] for i in range(self.n_players)]
        self.current_state = qt.basis(self.unitary.shape[0], 0)
        self.desired_state = self.unitary*self.current_state
        #self.current_state = self.desired_state
        #self.current_history = []
        self.winning = False
        self.goal_stars = q_SurfaceXYZ(self.desired_state)

    def reset_game(self):
        self.current_state = qt.basis(self.unitary.shape[0], 0)

    def new_game(self):
        self.unitary = qt.rand_unitary(2**self.n_players)
        self.player_colors = [[random.uniform(0,1), random.uniform(0,1), random.uniform(0,1)] for i in range(self.n_players)]
        self.current_state = qt.basis(self.unitary.shape[0], 0)
        self.desired_state = self.unitary*self.current_state
        self.winning = False
        self.goal_stars = q_SurfaceXYZ(self.desired_state)

    def more_qubits(self):
        self.n_players += 1
        self.new_game()

    def fewer_qubits(self):
        if self.n_players > 2:
            self.n_players -= 1
            self.new_game()

    def add_player(self, sid):
        if len(self.current_players) < self.n_players:
            self.current_players.append(sid)
            return True
        else:
            return False

    def remove_player(self, sid):
        for sid in self.current_players:
            self.current_players.remove(sid)
            return True
        else:
            return False

    def playerid_for_sid(self, sid):
        return self.current_players.index(sid)        

    def majorana_stars(self):
        return q_SurfaceXYZ(self.current_state)

    def mixed_stars(self):
        copy = self.current_state.copy()
        copy.dims = [[2]*self.n_players, [1]*self.n_players]
        mixed = [copy.ptrace(i) for i in range(self.n_players)]
        return [[qt.expect(qt.identity(2), mix)*qt.expect(qt.sigmax(), mix),\
                 qt.expect(qt.identity(2), mix)*qt.expect(qt.sigmay(), mix),\
                 qt.expect(qt.identity(2), mix)*qt.expect(qt.sigmaz(), mix)] for mix in mixed]

    def rotate_player(self, who, rot, dt=0.01):
        x, y, z = rot
        unitary = (2*math.pi*1j*dt*(x*qt.sigmax() + y*qt.sigmay() + z*qt.sigmaz())).expm()
        total_unitary = upgrade_tensor(unitary, who, self.n_players)
        total_unitary.dims = [[total_unitary.shape[0]], [total_unitary.shape[0]]]
        copy = self.current_state.copy()
        if total_unitary.dims[0] == self.current_state.dims[0]:
            self.current_state = total_unitary*self.current_state
        #print(copy)
        #print(total_unitary)
        #print("*")
        #sys.stdout.flush()
        #input()

    def entangle_players(self, a, b, dt, inverse):
        copy = self.current_state.copy()
        copy.dims = [[2]*self.n_players, [1]*self.n_players]

        dt = 0.01*dt
        if a != 0:
            copy = qt.tensor_swap(copy, (a, 0))
        if b != 1:
            if b == 0:
                copy = qt.tensor_swap(copy, (a, 1))
            else:
                copy = qt.tensor_swap(copy, (b, 1))

        full_op = qt.tensor(qt.cnot(), *[qt.identity(2)]*(self.n_players-2))

        full_unitary = (-2*math.pi*1j*dt*full_op).expm()
        if inverse:
            full_unitary = full_unitary.dag()
        full_unitary.dims = [[2]*self.n_players, [2]*self.n_players]

        copy = full_unitary*copy

        if b != 1:
            if b == 0:
                copy = qt.tensor_swap(copy, (1, a))
            else:
                copy = qt.tensor_swap(copy, (1, b))
        if a != 0:
            copy = qt.tensor_swap(copy, (0, a))


        copy.dims = self.current_state.dims
        self.current_state = copy
       

sio = socketio.Server(async_mode='eventlet')
app = Flask("quompiler")
app.debug = True
app.wsgi_app = socketio.Middleware(sio, app.wsgi_app)

thread = None
game = Game(2)

def loop():
    global game
    while True:
        #game.current_state = game.unitary*game.current_state
        surface_stars = game.majorana_stars()
        inner_stars = game.mixed_stars()
        overlap = game.current_state.overlap(game.desired_state)
        prob = (overlap*np.conjugate(overlap)).real
        win = 1 if np.isclose(prob, 1, rtol=0.005, atol=0.005) else 0
        for i, sid in enumerate(game.current_players):
            data = {"surface_stars": surface_stars,\
                    "inner_stars": inner_stars,
                    "player_id": game.playerid_for_sid(sid),\
                    "player_colors": game.player_colors,
                    "close": prob,
                    "win": win}
            sio.emit("update", json.dumps(data))
            #sio.emit("update", json.dumps(data))
        sio.sleep(0.01)

@app.route("/")
def root():
    global thread
    if thread is None:
        thread = sio.start_background_task(loop)
    return render_template("index.html")

@sio.on("connect")
def connect(sid, data):
    global game
    print(sid)
    sys.stdout.flush()
    game.add_player(sid)
    print("current_players %s" % game.current_players)
    sys.stdout.flush()
    sio.emit("goal", json.dumps({"goal_stars" : game.goal_stars}))
    
@sio.on("disconnect")
def disconnect(sid):
    global game
    game.remove_player(sid)
    print("current_players %s" % game.current_players)
    sys.stdout.flush()

@sio.on("qubit_rotation")
def qubit_rotation(sid, data):
    global game
    who = data["who"]
    rot = data["rot"]
    game.rotate_player(who, rot)
    #print(who)
    #print(rot)
    #sys.stdout.flush()

@sio.on("entangle_qubits")
def entangle_qubits(sid, data):
    global game
    #print("hi")
    #sys.stdout.flush()
    a = data["a"]
    b = data["b"]
    dt = data["dt"]
    inverse = data["inverse"]
    if dt > 0.0001:
        game.entangle_players(a, b, dt, inverse)

@sio.on("cmd")
def cmd(sid, data):
    global game
    if data["type"] == "reset":
        game.reset_game()
    elif data["type"] == "new":
        game.new_game()
        sio.emit("goal", json.dumps({"goal_stars" : game.goal_stars}))
    elif data["type"] == "fewer_qubits":
        game.fewer_qubits()
        sio.emit("goal", json.dumps({"goal_stars" : game.goal_stars}))
    elif data["type"] == "more_qubits":
        game.more_qubits()
        sio.emit("goal", json.dumps({"goal_stars" : game.goal_stars}))
import airsim

from onpolicy.envs.airsim_envs.airsim_socket import CustomAirsimClient
from socket import *
import pandas as pd
import time
import threading
import numpy as np
# from fixed_policy import *
import torch
import configparser
from onpolicy.envs.airsim_envs.airsim_env import AirSimDroneEnv
from onpolicy.algorithms.r_mappo.algorithm.r_actor_critic import R_Actor, R_Critic
# from patrol_policy import *
# from CarPolicy import CarPolicy



class Myconf(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=None)

    def optionxform(self, optionstr: str) -> str:
        return optionstr

def get_distance(x, y):
    return np.sqrt(np.power(x[0]-y[0] , 2) + np.power(x[1] - y[1], 2))

def _t2n(x):
    return x.detach().cpu().numpy()

def mission_points_init(center, number_of_drones):
    r = 800
    line_list = []
    for i in range(number_of_drones):
        pt = [0, 0]
        pt[0] = center[0] + r * np.cos(2 * np.pi / number_of_drones * i)
        pt[1] = center[1] + r * np.sin(2 * np.pi / number_of_drones * i)
        line_list.append(pt)
    return line_list

class AirWrapper:
    def __init__(self,  actor, airsim_env: AirSimDroneEnv, enemy_class=None):
        # _ = pd.read_table(file_name, sep='\t', header=None)
        # mission_list = []
        # for points in _[0]:
        #     mission_list.append(points.split(" "))
        self.enemy_class = enemy_class
        self.plot_car_flag = np.zeros(20)
        self.client = airsim.MultirotorClient('127.0.0.1')
        self.actor = actor
        self.env = airsim_env
        self.height = -40
        self.destroy_distance = 60
        self.remained_vehicle = self.env.client.assigned_blueprint.copy()
        self.num_agents = len(self.remained_vehicle)
        self.mission_state = np.zeros(100)
        self.mission_protect_teams = []
        self.people_dic = {0: 9, 1: 10, 2: 15, 3: 17,  4: 20}
        for ind in range(100):
            self.mission_protect_teams.append([])
        self.attack_flag = {} # 字典 bp_name:attack_target
        self.attacked_enemy = {}
        self.attacked_circle = {}
        self.enemy_position = {}
        self.mission_points = {}
        self.mission_attack = {}
        self.people_cf_dic = {} # 字典 记录参与解救人质的无人机分组 people_name:vehicle_name
        time.sleep(2)
        self.position_dict = {}
        self.people_flag = [False, False, False, False, False, False]
        self.intercept_flag = np.zeros(100)
        self.done_n = None
        self.destroyed_enemy = []
        self.agents = {}
        self.sorted_bp_dict = {}
        self.bp_names_list = []
        self.history_traj = {}
        self.task_cancel = False
        time.sleep(1)
        self.obs_n = self.reset()

    def reset(self):
        s = self.env.reset()
        cnt = 0
        for agent in self.env.agents:
            self.agents[agent.name] = agent
        for bp_name in self.remained_vehicle:
            self.position_dict[bp_name] = np.array([self.agents[bp_name].x, self.agents[bp_name].y])
            self.agents[bp_name].goal_position = self.position_dict[bp_name]
            cnt += 1
        return s

    def fly_run(self):
        _ = threading.Thread(target=self.fly_to_target, args=[])
        _.start()

    def fly_to_target(self):
        rnn_states_actor_n = []
        rnn_states_actor = np.zeros(
            (1, 1, 64),
            dtype=np.float32)
        masks = np.ones((1, 1), dtype=np.float32)
        for i in range(len(self.remained_vehicle)):
            rnn_states_actor_n.append(rnn_states_actor)

        action_n = np.zeros(len(self.remained_vehicle))
        while True:
            for i in range(len(self.remained_vehicle)):
                obs_tmp = self.obs_n[i].copy()
                obs_tmp = np.reshape(obs_tmp, (1, 5))
                tmp, _, rnn_states_actor_n[i] = self.actor(obs_tmp, rnn_states_actor_n[i], masks)
                action_n[i] = int(tmp[0][0])
                rnn_states_actor_n[i] = np.array(np.split(_t2n(rnn_states_actor_n[i]), 1))
                rnn_states_actor_n[i] = np.reshape(rnn_states_actor_n[i], (1, 1, 64))
            action_n = np.reshape(action_n, (self.num_agents, 1))
            self.obs_n, _, self.done_n, _ = self.env.step(action_n)
            for bp_name in self.remained_vehicle:
                self.position_dict[bp_name] = np.array([self.agents[bp_name].x, self.agents[bp_name].y])

    def cancel_task(self, bp_name):
        # self.task_cancel = True
        self.agents[bp_name].goal_position = self.position_dict[bp_name]

    def GoTo(self, bp_name, position):
        self.agents[bp_name].goal_position = position

    def Follow(self, bp_name, target_name=None):
        if not target_name:
            self.agents[bp_name].goal_position = self.position_dict[bp_name]
            return
        target_pose = self.client.simGetObjectPose(target_name)
        target_position = [target_pose.position.x_val, target_pose.position.y_val]
        self.agents[bp_name].goal_position = target_position

    def find_target(self, bp_name, target_name):
        target_pose = self.env.client.simGetObjectPose(target_name)
        target_position = [target_pose.position.x_val, target_pose.position.y_val]
        if get_distance(target_position, self.position_dict[bp_name]) < 10:
            return True
        else:
            return False

    def get_agents_name(self):
        return self.env.client.listVehicles()

    def find_system_objects(self, object_name):
        py_list = self.client.simListSceneObjects()
        return [s for s in py_list if object_name in s]

    def get_drone_position(self, drone_name):
        return self.position_dict[drone_name]

    def get_target_pose(self, target_name):
        return self.client.simGetObjectPose(target_name).position


if __name__ == "__main__":
    default_cfg = 'D:/crazyflie-simulation/airsim_mappo/onpolicy/envs/airsim_envs/cfg/default.cfg'
    cfg = Myconf()
    cfg.read(default_cfg)
    for each in cfg.items("algorithm"):
        cfg.__dict__[each[0]] = each[1]
    if cfg.getboolean('algorithm', 'cuda') and torch.cuda.is_available():
        print("choose to use gpu...")
        device = torch.device("cuda:0")
        torch.set_num_threads(cfg.getint('algorithm', 'n_training_threads'))
        if cfg.getboolean('algorithm', 'cuda_deterministic'):
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
    else:
        print("choose to use cpu...")
        device = torch.device("cpu")
        torch.set_num_threads(cfg.getint('algorithm', 'n_training_threads'))

    # seed
    torch.manual_seed(cfg.getint('algorithm', 'seed'))
    torch.cuda.manual_seed_all(cfg.getint('algorithm', 'seed'))
    np.random.seed(cfg.getint('algorithm', 'seed'))

    # env init
    env = AirSimDroneEnv(cfg)
    num_agents = cfg.getint('options', 'num_of_drone')

    config = {
        "cfg": cfg,
        "envs": env,
        "num_agents": num_agents,
        "device": device
    }

    # load model
    policy_actor_state_dict = torch.load(str(cfg.get("algorithm", 'model_dir')) + '/actor.pt')
    actor1 = R_Actor(config['cfg'], config['envs'].observation_space[0], config['envs'].action_space[0],
                     config['device'])
    actor1.load_state_dict(policy_actor_state_dict)

    drones = AirWrapper(actor1, env)
    drones.GoTo('cf_friend_3', [drones.get_target_pose('people2_5').x_val, drones.get_target_pose('people2_5').y_val])
    # patrol_drones.fly_run()
    drones.fly_run()
    print("done")


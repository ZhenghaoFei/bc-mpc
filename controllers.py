import numpy as np
from cost_functions import trajectory_cost_fn
import time
import copy

class Controller():
    def __init__(self):
        pass

    # Get the appropriate action(s) for this state(s)
    def get_action(self, state):
        pass


class RandomController(Controller):
    def __init__(self, env):
        """ YOUR CODE HERE """
        self.env = env

    def get_action(self, state):

        """ YOUR CODE HERE """
        """ Your code should randomly sample an action uniformly from the action space """
        return self.env.action_space.sample()

class MPCcontroller(Controller):
    """ Controller built using the MPC method outlined in https://arxiv.org/abs/1708.02596 """
    def __init__(self, 
                 env, 
                 dyn_model, 
                 horizon=5, 
                 cost_fn=None, 
                 num_simulated_paths=10,
                 gamma=1.,
                 ):
        self.env = env
        self.dyn_model = dyn_model
        self.horizon = horizon
        self.cost_fn = cost_fn
        self.num_simulated_paths = num_simulated_paths
        self.gamma = gamma

    def sample_random_actions(self):
      
        # sample random action trajectories
        # actions = []
        # for n in range(self.num_simulated_paths):
        #     for h in range(self.horizon):
        #         actions.append(self.env.action_space.sample())

        # np_action_paths = np.asarray(actions)
        # np_action_paths = np.reshape(np_action_paths, [self.horizon, self.num_simulated_paths, -1])
        np_action_paths = np.random.uniform(low=self.env.action_space.low, high=self.env.action_space.high , size=[self.horizon, self.num_simulated_paths, len(self.env.action_space.high)])

        return np_action_paths

    def get_action(self, state):
        """ YOUR CODE HERE """
        """ Note: be careful to batch your simulations through the model for speed """
        action_paths = self.sample_random_actions()

        # get init observations and copy num_simulated_paths times
        states = np.tile(state, [self.num_simulated_paths, 1])

        states_paths_all = []
        states_paths_all.append(states)


        for i in range(self.horizon):
            states = self.dyn_model.predict(states, action_paths[i, :, :])
            states_paths_all.append(states)

        # evaluate trajectories
        states_paths_all = np.asarray(states_paths_all)

        # batch cost function
        states_paths = states_paths_all[:-1, :, :]
        states_nxt_paths = states_paths_all[1:, :, :]

        costs = trajectory_cost_fn(self.cost_fn, states_paths, action_paths, states_nxt_paths)

        min_cost_path = np.argmin(costs)
        opt_cost = costs[min_cost_path]
        opt_action_path = action_paths[:, min_cost_path, :]
        opt_action = copy.copy(opt_action_path[0])

        # print("MPC imagine min cost: ", opt_cost)
        return opt_action

class MPCcontrollerReward(Controller):
    """ Controller built using the MPC method outlined in https://arxiv.org/abs/1708.02596 """
    def __init__(self, 
                 env, 
                 dyn_model, 
                 horizon=5, 
                 cost_fn=None, 
                 num_simulated_paths=10,
                 gamma=1.,

                 ):
        self.env = env
        self.dyn_model = dyn_model
        self.horizon = horizon
        self.cost_fn = cost_fn
        self.num_simulated_paths = num_simulated_paths
        self.gamma = gamma

    def sample_random_actions(self):
      
        # sample random action trajectories
        actions = []
        for n in range(self.num_simulated_paths):
            for h in range(self.horizon):
                actions.append(self.env.action_space.sample())

        np_action_paths = np.asarray(actions)
        np_action_paths = np.reshape(np_action_paths, [self.horizon, self.num_simulated_paths, -1])

        return np_action_paths

    def get_action(self, state):

        """ YOUR CODE HERE """
        """ Note: be careful to batch your simulations through the model for speed """

        action_paths = self.sample_random_actions()

        # get init observations and copy num_simulated_paths times
        states = np.tile(state, [self.num_simulated_paths, 1])

        # states_paths_all = []
        rewards_all = []
        # states_paths_all.append(states)

        for i in range(self.horizon):
            states, reward = self.dyn_model.predict(states, action_paths[i, :, :])
            # states_paths_all.append(states)
            rewards_all.append(reward*self.gamma**i)

        # # evaluate trajectories
        # states_paths_all = np.asarray(states_paths_all)

        # # batch cost function
        # states_paths = states_paths_all[:-1, :, :]
        # states_nxt_paths = states_paths_all[1:, :, :]

        # costs = trajectory_cost_fn(self.cost_fn, states_paths, action_paths, states_nxt_paths)

        rewards_all = np.asarray(rewards_all)
        rewards_all = np.sum(rewards_all, axis=0)
        rewards_all = np.reshape(rewards_all, [-1])
        min_cost_path = np.argmax(rewards_all)
        opt_imgreward = rewards_all[min_cost_path]
        opt_action_path = action_paths[:, min_cost_path, :]
        opt_action = copy.copy(opt_action_path[0])

        # print("MPC imagine min cost: ", opt_imgreward)
        return opt_action

class MPCcontrollerPolicyNet(Controller):
    """ Controller built using the MPC method outlined in https://arxiv.org/abs/1708.02596 """
    def __init__(self, 
                 env, 
                 dyn_model,
                 policy_net, 
                 explore=1.,
                 self_exp=True,
                 horizon=5, 
                 cost_fn=None, 
                 num_simulated_paths=10,
                 ):
        self.env = env
        self.dyn_model = dyn_model
        self.policy_net = policy_net
        self.horizon = horizon
        self.cost_fn = cost_fn
        self.num_simulated_paths = num_simulated_paths
        self.self_exp = self_exp
        self.explore = explore

    def sample_random_actions(self):
      
        # sample random action trajectories
        np_action_paths = np.random.uniform(low=self.env.action_space.low, high=self.env.action_space.high , size=[self.horizon, self.num_simulated_paths, len(self.env.action_space.high)])

        return np_action_paths


    def get_action(self, state):
        """ YOUR CODE HERE """
        """ Note: be careful to batch your simulations through the model for speed """
        exploration = self.sample_random_actions()

        # get init observations and copy num_simulated_paths times
        states = np.tile(state, [self.num_simulated_paths, 1])

        states_paths_all = []
        action_paths = []
        states_paths_all.append(states)

        for i in range(self.horizon):
            if self.self_exp:
                actions, _ = self.policy_net.act(states, stochastic=True)
            else:
                actions, _ = self.policy_net.act(states, stochastic=False)
                # actions += np.random.rand(self.num_simulated_paths, self.env.action_space.shape[0]) * (2*self.explore) - self.explore

                actions = (1 - self.explore) * actions + self.explore * exploration[i, :, :]

            states = self.dyn_model.predict(states, actions)

            # states = self.dyn_model.predict(states, action_paths[i, :, :])
            states_paths_all.append(states)
            action_paths.append(actions)

        # evaluate trajectories
        states_paths_all = np.asarray(states_paths_all)
        action_paths = np.asarray(action_paths)


        # batch cost function
        states_paths = states_paths_all[:-1, :, :]
        states_nxt_paths = states_paths_all[1:, :, :]

        # print("action_paths: ", action_paths.shape)
        # print("states_paths: ", states_paths.shape)
        # print("states_nxt_paths: ", states_nxt_paths.shape)

        costs = trajectory_cost_fn(self.cost_fn, states_paths, action_paths, states_nxt_paths)

        min_cost_path = np.argmin(costs)
        opt_cost = costs[min_cost_path]
        opt_action_path = action_paths[:, min_cost_path, :]
        opt_action = copy.copy(opt_action_path[0])

        # print("MPC imagine min cost: ", opt_cost)
        return opt_action

    def get_action_mcs(self, state):
        """ YOUR CODE HERE """
        """ Note: be careful to batch your simulations through the model for speed """
        exploration = self.sample_random_actions()

        # get init observations and copy num_simulated_paths times
        states = np.tile(state, [self.num_simulated_paths, 1])

        states_paths_all = []
        action_paths = []
        states_paths_all.append(states)

        for i in range(self.horizon):
            if self.self_exp:
                actions, _ = self.policy_net.act(states, stochastic=True)
            else:
                actions, _ = self.policy_net.act(states, stochastic=False)
                # actions += np.random.rand(self.num_simulated_paths, self.env.action_space.shape[0]) * (2*self.explore) - self.explore

                actions = (1 - self.explore) * actions + self.explore * exploration[i, :, :]

            states = self.dyn_model.predict(states, actions)

            # states = self.dyn_model.predict(states, action_paths[i, :, :])
            states_paths_all.append(states)
            action_paths.append(actions)

        # evaluate trajectories
        states_paths_all = np.asarray(states_paths_all)
        action_paths = np.asarray(action_paths)


        # batch cost function
        states_paths = states_paths_all[:-1, :, :]
        states_nxt_paths = states_paths_all[1:, :, :]

        # print("action_paths: ", action_paths.shape)
        # print("states_paths: ", states_paths.shape)
        # print("states_nxt_paths: ", states_nxt_paths.shape)

        costs = trajectory_cost_fn(self.cost_fn, states_paths, action_paths, states_nxt_paths)

        min_cost_path = np.argmin(costs)
        opt_cost = costs[min_cost_path]
        opt_action_path = action_paths[:, min_cost_path, :]
        opt_action = copy.copy(opt_action_path[0])

        # print("MPC imagine min cost: ", opt_cost)
        return opt_action

class MPCcontrollerPolicyNetReward(Controller):
    """ Controller built using the MPC method outlined in https://arxiv.org/abs/1708.02596 """
    def __init__(self, 
                 env, 
                 dyn_model,
                 policy_net, 
                 explore=1.,
                 self_exp=True,
                 horizon=5, 
                 cost_fn=None, 
                 num_simulated_paths=10,
                 gamma=1.
                 ):
        self.env = env
        self.dyn_model = dyn_model
        self.policy_net = policy_net
        self.horizon = horizon
        self.cost_fn = cost_fn
        self.num_simulated_paths = num_simulated_paths
        self.self_exp = self_exp
        self.explore = explore
        self.gamma = gamma

    def sample_random_actions(self):
      
        # sample random action trajectories
        np_action_paths = np.random.uniform(low=self.env.action_space.low, high=self.env.action_space.high , size=[self.horizon, self.num_simulated_paths, len(self.env.action_space.high)])

        return np_action_paths

    def get_action(self, state):

        """ YOUR CODE HERE """
        """ Note: be careful to batch your simulations through the model for speed """
        exploration = self.sample_random_actions()

        # get init observations and copy num_simulated_paths times
        states = np.tile(state, [self.num_simulated_paths, 1])
        states_paths_all = []
        action_paths = []
        states_paths_all.append(states)

        rewards_all = []
        action_paths = []

        for i in range(self.horizon):
            if self.self_exp:
                actions, _ = self.policy_net.act(states, stochastic=True)
            else:
                actions, _ = self.policy_net.act(states, stochastic=False)
                # actions += np.random.rand(self.num_simulated_paths, self.env.action_space.shape[0]) * (2*self.explore) - self.explore
                actions = (1 - self.explore) * actions + self.explore * exploration[i, :, :]

            states, reward = self.dyn_model.predict(states, actions)

            # states = self.dyn_model.predict(states, action_paths[i, :, :])
            states_paths_all.append(states)
            action_paths.append(actions)
            rewards_all.append(reward)

        # evaluate trajectories
        action_paths = np.asarray(action_paths)
        rewards_all = np.asarray(rewards_all)

        rewards_all = np.sum(rewards_all, axis=0)
        rewards_all = np.reshape(rewards_all, [-1])

        print("rewards_all", rewards_all.shape)

        max_reward_path = np.argmax(rewards_all)
        opt_imgreward = rewards_all[max_reward_path]
        opt_action_path = action_paths[:, max_reward_path, :]
        opt_action = copy.copy(opt_action_path[0])

        return opt_action

class MCTScontrollerPolicyNetReward(Controller):
    def __init__(self, 
                 env, 
                 dyn_model,
                 policy_net, 
                 explore=1.,
                 self_exp=True,
                 horizon=5, 
                 cost_fn=None, 
                 num_first_stage_actions=10, 
                 random_path_per_action=10,
                 random_first_stage_action = False,
                 ):

        self.env = env
        self.dyn_model = dyn_model
        self.policy_net = policy_net
        self.horizon = horizon
        self.cost_fn = cost_fn
        self.num_first_stage_actions = num_first_stage_actions
        self.random_path_per_action = random_path_per_action
        self.self_exp = self_exp
        self.explore = explore
        self.random_first_stage_action = random_first_stage_action

    def sample_random_actions(self):
      
        # sample random action trajectories
        np_action_paths = np.random.uniform(low=self.env.action_space.low, high=self.env.action_space.high , size=[self.horizon, self.num_simulated_paths, len(self.env.action_space.high)])

        return np_action_paths

    def get_action(self, state):

        best_action1_idx = 0
        best_reward = None
        action_1s = []
        state_init = np.expand_dims(state, axis=0)
        states_all_actions = []
        reward_1s = []
        for action_idx in range(self.num_first_stage_actions):
            total_reward = 0

            if self.random_first_stage_action:
                action_1 = self.env.action_space.sample()
                action_1 = np.expand_dims(action_1, axis=0)
            else:
                if self.self_exp:
                    action_1, _ = self.policy_net.act(state_init, stochastic=True)
                else:
                    action_1, _ = self.policy_net.act(state_init, stochastic=False)
            
            state_1, reward_1 = self.dyn_model.predict(state_init, action_1)
            reward_1s.append(reward_1[0][0])
            action_1s.append(action_1)

            # following stages
            rewards_all = []
            states = np.tile(state_1, [self.random_path_per_action, 1])
            states_all_actions.append(states)
        
        states_all_actions = np.asarray(states_all_actions)
        
        states = states_all_actions.reshape((-1,state.shape[0]))

        for i in range(self.horizon):

            actions, _ = self.policy_net.act(states, stochastic=False)
            
            # if self.self_exp:
            #     actions, _ = self.policy_net.act(states, stochastic=True)
            # else:
            #     actions, _ = self.policy_net.act(states, stochastic=False)

            states, reward = self.dyn_model.predict(states, actions)
            # states = self.dyn_model.predict(states, action_paths[i, :, :])
            rewards_all.append(reward)

        rewards_all = np.asarray(rewards_all)
        rewards_all = np.sum(rewards_all, axis=0)

        rewards_all = rewards_all.reshape((self.num_first_stage_actions, -1))

        rewards_all_mean = np.mean(rewards_all, axis=1)
        reward_1s = np.asarray(reward_1s)
        total_rewards = reward_1s + rewards_all_mean
        

        best_action1_idx = np.argmax(total_rewards)

        opt_action = action_1s[best_action1_idx]

        return opt_action











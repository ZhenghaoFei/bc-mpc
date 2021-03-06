import numpy as np
import tensorflow as tf
import gym
from dynamics import NNDynamicsModel
from controllers import MPCcontroller, RandomController, MPCcontroller_BC
from cost_functions import cheetah_cost_fn, trajectory_cost_fn
import time
import logz
import os
import copy
import matplotlib.pyplot as plt
from cheetah_env import HalfCheetahEnvNew
from data_buffer import DataBuffer, DataBuffer_SA
from behavioral_cloning import BCnetwork

# ===========================
# Training parameters for bc
# ===========================
TEST_EPOCH = 5000
BATCH_SIZE_BC = 128
LOAD_MODEL = True
CHECKPOINT_DIR = 'checkpoints/'

############################


def sample(env, 
           controller, 
           num_paths=10, 
           horizon=1000, 
           render=False,
           verbose=False):
    """
        Write a sampler function which takes in an environment, a controller (either random or the MPC controller), 
        and returns rollouts by running on the env. 
        Each path can have elements for observations, next_observations, rewards, returns, actions, etc.
    """
    """ YOUR CODE HERE """

    paths = []
    for i in range(num_paths):
        # print("random data iter ", i)
        st = env.reset_model()
        path = {'observations': [], 'actions': [], 'next_observations':[]}

        for t in range(horizon):
           at = controller.get_action(st)
           st_next, _, _, _ = env.step(at)

           path['observations'].append(st)
           path['actions'].append(at)
           path['next_observations'].append(st_next)
           st = st_next

        paths.append(path)

    return paths

# Utility to compute cost a path for a given cost function
def path_cost(cost_fn, path):
    return trajectory_cost_fn(cost_fn, path['observations'], path['actions'], path['next_observations'])

def compute_normalization(data):
    """
    Write a function to take in a dataset and compute the means, and stds.
    Return 6 elements: mean of s_t, std of s_t, mean of (s_t+1 - s_t), std of (s_t+1 - s_t), mean of actions, std of actions
    """

    """ YOUR CODE HERE """
    # Nomalization statistics
    sample_state, sample_action, sample_nxt_state, sample_state_delta = data.sample(data.size)
    mean_obs = np.mean(sample_state, axis=0)
    mean_action = np.mean(sample_action, axis=0)
    mean_nxt_state = np.mean(sample_nxt_state, axis=0)
    mean_deltas = np.mean(sample_state_delta, axis=0)

    std_obs = np.std(sample_state, axis=0)
    std_action = np.std(sample_action, axis=0)
    std_nxt_state = np.std(sample_nxt_state, axis=0)
    std_deltas = np.std(sample_state_delta, axis=0)

    return [mean_obs, std_obs, mean_action, std_action, mean_nxt_state, std_nxt_state, mean_deltas, std_deltas]


def plot_comparison(env, dyn_model):
    """
    Write a function to generate plots comparing the behavior of the model predictions for each element of the state to the actual ground truth, using randomly sampled actions. 
    """
    """ YOUR CODE HERE """
    pass

def behavioral_cloning(sess, env, bc_network, mpc_controller, env_horizon, bc_data_buffer):

    Training_epoch = 10000
    DAGGER = True
    # Imitation policy
    print("Behavioral cloning ..... ", " bc buffer size: ", bc_data_buffer.size)
    path = {'observations': [], 'actions': []}
    bc_network.train(bc_data_buffer, steps=1)

    for EP in range(Training_epoch):
        loss = bc_network.train(bc_data_buffer, steps=1)

        if EP % 100 == 0:
            print('epcho: ', EP, ' loss: ', loss)
            behavioral_cloning_test(sess, env, bc_network, env_horizon)

        if DAGGER and EP%500 ==0 and EP!=0:
            print("Daggering")

            st = env.reset_model()
            return_ = 0

            for j in range(env_horizon):
                at = bc_network.predict(np.reshape(st, [1, -1]))[0]
                expert_at = mpc_controller.get_action(st)
                nxt_st, r, _, _ = env.step(at)
                path['observations'].append(st)
                path['actions'].append(expert_at)
                st = nxt_st
                return_ += r

            # add into buffers
            for n in range(len(path['observations'])):
                bc_data_buffer.add(path['observations'][n], path['actions'][n])
            print("now training data size: ", bc_data_buffer.size)

def behavioral_cloning_test(sess, env, bc_network, env_horizon):
    print('---------- bc testing ---------')
    st = env.reset_model()
    returns = 0

    for j in range(env_horizon):
        at = bc_network.predict(np.reshape(st, [1, -1]))[0]
        # print(at)
        nxt_st, r, _, _ = env.step(at)
        st = nxt_st
        returns += r

    print("return: ", returns)

def train(env, 
         cost_fn,
         logdir=None,
         render=False,
         learning_rate=1e-3,
         onpol_iters=10,
         dynamics_iters=60,
         batch_size=512,
         num_paths_random=10, 
         num_paths_onpol=10, 
         num_simulated_paths=10000,
         env_horizon=1000, 
         mpc_horizon=15,
         n_layers=2,
         size=500,
         activation=tf.nn.relu,
         output_activation=None
         ):
    # tracker = SummaryTracker()

    """

    Arguments:

    onpol_iters                 Number of iterations of onpolicy aggregation for the loop to run. 

    dynamics_iters              Number of iterations of training for the dynamics model
    |_                          which happen per iteration of the aggregation loop.

    batch_size                  Batch size for dynamics training.

    num_paths_random            Number of paths/trajectories/rollouts generated 
    |                           by a random agent. We use these to train our 
    |_                          initial dynamics model.
    
    num_paths_onpol             Number of paths to collect at each iteration of
    |_                          aggregation, using the Model Predictive Control policy.

    num_simulated_paths         How many fictitious rollouts the MPC policy
    |                           should generate each time it is asked for an
    |_                          action.

    env_horizon                 Number of timesteps in each path.

    mpc_horizon                 The MPC policy generates actions by imagining 
    |                           fictitious rollouts, and picking the first action
    |                           of the best fictitious rollout. This argument is
    |                           how many timesteps should be in each fictitious
    |_                          rollout.

    n_layers/size/activations   Neural network architecture arguments. 

    """

    # logz.configure_output_dir(logdir)

    #========================================================
    # 
    # First, we need a lot of data generated by a random
    # agent, with which we'll begin to train our dynamics
    # model.

    """ YOUR CODE HERE """

    # Print env info
    print("-------- env info --------")
    print("observation_space: ", env.observation_space.shape)
    print("action_space: ", env.action_space.shape)
    print(" ")


    random_controller = RandomController(env)
    data_buffer = DataBuffer()
    bc_data_buffer = DataBuffer_SA(100000)

    # sample path
    print("collecting random data .....  ")
    paths = sample(env, 
               random_controller, 
               num_paths=num_paths_random, 
               horizon=env_horizon, 
               render=False,
               verbose=False)

    # add into buffer
    for path in paths:
        for n in range(len(path['observations'])):
            data_buffer.add(path['observations'][n], path['actions'][n], path['next_observations'][n])



    #========================================================
    # 
    # The random data will be used to get statistics (mean
    # and std) for the observations, actions, and deltas
    # (where deltas are o_{t+1} - o_t). These will be used
    # for normalizing inputs and denormalizing outputs
    # from the dynamics network. 
    # 
    print("data buffer size: ", data_buffer.size)

    normalization = compute_normalization(data_buffer)

    #========================================================
    # 
    # Build dynamics model and MPC controllers and Behavioral cloning network.
    # 
    sess = tf.Session()

    dyn_model = NNDynamicsModel(env=env, 
                                n_layers=n_layers, 
                                size=size, 
                                activation=activation, 
                                output_activation=output_activation, 
                                normalization=normalization,
                                batch_size=batch_size,
                                iterations=dynamics_iters,
                                learning_rate=learning_rate,
                                sess=sess)

    mpc_controller = MPCcontroller(env=env, 
                                   dyn_model=dyn_model, 
                                   horizon=mpc_horizon, 
                                   cost_fn=cost_fn, 
                                   num_simulated_paths=num_simulated_paths)

    bc_net = BCnetwork(sess, env, BATCH_SIZE_BC, learning_rate)

    mpc_controller_bc = MPCcontroller_BC(env=env, 
                                   dyn_model=dyn_model, 
                                   bc_network=bc_net,
                                   horizon=mpc_horizon, 
                                   cost_fn=cost_fn, 
                                   num_simulated_paths=num_simulated_paths)



    #========================================================
    # 
    # Tensorflow session building.
    # 
    sess.__enter__()
    tf.global_variables_initializer().run()

    # init or load checkpoint with saver
    saver = tf.train.Saver()

    checkpoint = tf.train.get_checkpoint_state(CHECKPOINT_DIR)

    if checkpoint and checkpoint.model_checkpoint_path:
        saver.restore(sess, checkpoint.model_checkpoint_path)
        print("checkpoint loaded:", checkpoint.model_checkpoint_path)
    else:
        print("Could not find old checkpoint")
        if not os.path.exists(CHECKPOINT_DIR):
          os.mkdir(CHECKPOINT_DIR)  
    # #========================================================
    # # 
    # # Take multiple iterations of onpolicy aggregation at each iteration refitting the dynamics model to current dataset and then taking onpolicy samples and aggregating to the dataset. 
    # # Note: You don't need to use a mixing ratio in this assignment for new and old data as described in https://arxiv.org/abs/1708.02596
    # # 

    for itr in range(onpol_iters):
        """ YOUR CODE HERE """
        print("onpol_iters: ", itr)
        # dyn_model.fit(data_buffer)

        # saver.save(sess, CHECKPOINT_DIR)

        returns = []
        costs = []

        print("data buffer size: ", data_buffer.size)

        st = env.reset_model()
        path = {'observations': [], 'actions': [], 'next_observations':[]}
        # tracker.print_diff()

        return_ = 0

        for i in range(env_horizon):
            if render:
                env.render()
            # print("env_horizon: ", i)   
            at = mpc_controller.get_action(st)
            # at = random_controller.get_action(st)
            # at = mpc_controller_bc.get_action(st)

            st_next, env_reward, _, _ = env._step(at)
            path['observations'].append(st)
            path['actions'].append(at)
            path['next_observations'].append(st_next)
            st = st_next
            return_ += env_reward

        # cost & return
        cost =path_cost(cost_fn, path)
        costs.append(cost)
        returns.append(return_)
        print("total return: ", return_)
        print("costs: ", cost)

        # add into buffers
        for n in range(len(path['observations'])):
            data_buffer.add(path['observations'][n], path['actions'][n], path['next_observations'][n])
            bc_data_buffer.add(path['observations'][n], path['actions'][n])

    behavioral_cloning(sess, env, bc_net, mpc_controller, env_horizon, bc_data_buffer)




    #     # LOGGING
    #     # Statistics for performance of MPC policy using
    #     # our learned dynamics model
    #     logz.log_tabular('Iteration', itr)
    #     logz.log_tabular('Average_BC_Return', np.mean(bc_returns))

    #     # In terms of cost function which your MPC controller uses to plan
    #     logz.log_tabular('AverageCost', np.mean(costs))
    #     logz.log_tabular('StdCost', np.std(costs))
    #     logz.log_tabular('MinimumCost', np.min(costs))
    #     logz.log_tabular('MaximumCost', np.max(costs))
    #     # In terms of true environment reward of your rolled out trajectory using the MPC controller
    #     logz.log_tabular('AverageReturn', np.mean(returns))
    #     logz.log_tabular('StdReturn', np.std(returns))
    #     logz.log_tabular('MinimumReturn', np.min(returns))
    #     logz.log_tabular('MaximumReturn', np.max(returns))

    #     logz.dump_tabular()

def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--env_name', type=str, default='HalfCheetah-v1')
    # Experiment meta-params
    parser.add_argument('--exp_name', type=str, default='mb_mpc')
    parser.add_argument('--seed', type=int, default=3)
    parser.add_argument('--render', action='store_true')
    # Training args
    parser.add_argument('--learning_rate', '-lr', type=float, default=1e-3)
    parser.add_argument('--onpol_iters', '-n', type=int, default=5)
    parser.add_argument('--dyn_iters', '-nd', type=int, default=260)
    parser.add_argument('--batch_size', '-b', type=int, default=512)
    # Data collection
    parser.add_argument('--random_paths', '-r', type=int, default=10)
    parser.add_argument('--onpol_paths', '-d', type=int, default=2)
    parser.add_argument('--simulated_paths', '-sp', type=int, default=1000)
    parser.add_argument('--ep_len', '-ep', type=int, default=1000)
    # Neural network architecture args
    parser.add_argument('--n_layers', '-l', type=int, default=2)
    parser.add_argument('--size', '-s', type=int, default=500)
    # MPC Controller
    parser.add_argument('--mpc_horizon', '-m', type=int, default=10)
    args = parser.parse_args()

    # Set seed
    np.random.seed(args.seed)
    tf.set_random_seed(args.seed)

    # Make data directory if it does not already exist
    if not(os.path.exists('data')):
        os.makedirs('data')
    logdir = args.exp_name + '_' + args.env_name + '_' + time.strftime("%d-%m-%Y_%H-%M-%S")
    logdir = os.path.join('data', logdir)
    if not(os.path.exists(logdir)):
        os.makedirs(logdir)

    # Make env
    if args.env_name is "HalfCheetah-v1":
        env = HalfCheetahEnvNew()
        cost_fn = cheetah_cost_fn
    train(env=env, 
                 cost_fn=cost_fn,
                 logdir=logdir,
                 render=args.render,
                 learning_rate=args.learning_rate,
                 onpol_iters=args.onpol_iters,
                 dynamics_iters=args.dyn_iters,
                 batch_size=args.batch_size,
                 num_paths_random=args.random_paths, 
                 num_paths_onpol=args.onpol_paths, 
                 num_simulated_paths=args.simulated_paths,
                 env_horizon=args.ep_len, 
                 mpc_horizon=args.mpc_horizon,
                 n_layers = args.n_layers,
                 size=args.size,
                 activation=tf.nn.relu,
                 output_activation=None,
                 )

if __name__ == "__main__":
    main()

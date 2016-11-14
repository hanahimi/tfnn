import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class RNNDataSet(object):
    def __init__(self, basket_len=[40, 100, 300, 1000]):
        self.basket_len = basket_len
        self.features = {}   # in order of [40, 100, 300, 10000]
        self.targets = {}    # in order of [40, 100, 300, 10000]
        self._has_batch = False
        self._batch_time_index = 0
        for bl in basket_len:
            # feature panel, shape (sample_num, time_steps, input_size)
            f_pn = pd.read_pickle(
                'datasets/RNN_F(my_displacement+gap)T(my_gap)/b{}_f(dis+gap).pickle'.format(bl)).as_matrix()
            # target panel, shape (sample_num, time_steps, output_size)
            t_pn = pd.read_pickle(
                'datasets/RNN_F(my_displacement+gap)T(my_gap)/b{}_t(dis).pickle'.format(bl)).as_matrix()
            self.features[bl] = f_pn
            self.targets[bl] = t_pn

    def normalize(self, config):
        for bl in self.basket_len:
            f_shape = self.features[bl].shape
            f = self.features[bl].reshape((-1, config.input_size))
            f = f * np.array([[
                config.displacement_scale,
                config.gap_scale
            ]]) + np.array([[
                config.displacement_bias,
                config.gap_bias
            ]])
            self.features[bl] = f.reshape(f_shape)

    def next(self, batch_size, time_steps):
        while True:
            if not self._has_batch:
                self.batch_features, self.batch_targets, self.selected_basket_len = self._get_batch(batch_size)
                self._has_batch = True
            else:
                if self._batch_time_index + time_steps <= self.selected_basket_len:
                    if self._batch_time_index == 0:
                        is_initial_state = True
                    else:
                        is_initial_state = False
                    results = [
                        self.batch_features[:, self._batch_time_index: self._batch_time_index+time_steps, :],
                        self.batch_targets[:, self._batch_time_index: self._batch_time_index+time_steps, :],
                        is_initial_state
                    ]
                    self._batch_time_index += time_steps
                    break
                else:
                    self._batch_time_index = 0
                    self._has_batch = False
                    continue
        return results

    def _get_batch(self, batch_size):
        selected_basket_len = np.random.choice(self.basket_len)
        basket_features = self.features[selected_basket_len]
        basket_targets = self.targets[selected_basket_len]
        sample_num = basket_features.shape[0]
        sample_index = np.random.randint(0, sample_num, batch_size)
        batch_features = basket_features[sample_index, :, :]
        batch_targets = basket_targets[sample_index, :, :]
        # return batches with different time steps
        return [batch_features, batch_targets, selected_basket_len]


class DataSet(object):
    def __init__(self, path):
        # including [deri_v, delta_x, dx, dv, deri_a_clipped, v_l]
        df = pd.read_pickle(path)
        self._road_data = df.loc[:,
                          ['Vehicle_ID', 'deri_v', 'displacement', 'dx', 'dv', 'deri_a_clipped', 'v_l']].dropna()
        self._car_ids = np.unique(self._road_data['Vehicle_ID'])
        self._id_index = 0

    def put_in_basket(self, basket_len=[40, 100, 300, 1000]):
        b0 = [[], []]
        b1 = [[], []]
        b2 = [[], []]
        b3 = [[], []]
        for car_id in self._car_ids:
            features = self._road_data[self._road_data['Vehicle_ID'] == car_id][['displacement', 'dx']].copy()
            targets = features['displacement'].iloc[1:].copy()
            targets_steps = targets.shape[0]
            start_pointer = 0
            # filter the data that have time step > 1000
            while targets_steps - start_pointer >= basket_len[-1]:
                b0[0].append(features.iloc[start_pointer: start_pointer + basket_len[-1]])
                b0[1].append(targets.iloc[start_pointer: start_pointer + basket_len[-1]])
                start_pointer += basket_len[-1]
            # filter the data that have time step > 300
            while targets_steps - start_pointer >= basket_len[-2]:
                b1[0].append(features.iloc[start_pointer: start_pointer + basket_len[-2]])
                b1[1].append(targets.iloc[start_pointer: start_pointer + basket_len[-2]])
                start_pointer += basket_len[-2]
            # filter the data that have time step > 100
            while targets_steps - start_pointer >= basket_len[-3]:
                b2[0].append(features.iloc[start_pointer: start_pointer + basket_len[-3]])
                b2[1].append(targets.iloc[start_pointer: start_pointer + basket_len[-3]])
                start_pointer += basket_len[-3]
            # filter the data that have time step > 40
            while targets_steps - start_pointer >= basket_len[-4]:
                b3[0].append(features.iloc[start_pointer: start_pointer + basket_len[-4]])
                b3[1].append(targets.iloc[start_pointer: start_pointer + basket_len[-4]])
                start_pointer += basket_len[-4]
        # feature = b0[0][0] (one sample) with shape of (basket_time_steps, inputs)
        # target = b0[1][0] (one sample) with shape of (basket_time_steps, )
        # features = b0[0] ==> shape (basket_time_steps, inputs, sample_num) ==> transpose to (sample_num, basket_time_steps, inputs)
        # targets = b0[1] ==> shape (outputs, basket_time_steps, sample_num) ==> transpose to (sample_num, basket_time_steps, outputs)
        base_dir = 'datasets/RNN_F(my_displacement+gap)T(my_gap)'
        pd.Panel(np.dstack(b0[0]).transpose(2, 0, 1)).to_pickle(
            '{0}/b{1}_f(dis+gap).pickle'.format(base_dir, basket_len[-1]))
        pd.Panel(np.dstack(b0[1]).transpose(2, 1, 0)).to_pickle(
            '{0}/b{1}_t(dis).pickle'.format(base_dir, basket_len[-1]))
        pd.Panel(np.dstack(b1[0]).transpose(2, 0, 1)).to_pickle(
            '{0}/b{1}_f(dis+gap).pickle'.format(base_dir, basket_len[-2]))
        pd.Panel(np.dstack(b1[1]).transpose(2, 1, 0)).to_pickle(
            '{0}/b{1}_t(dis).pickle'.format(base_dir, basket_len[-2]))
        pd.Panel(np.dstack(b2[0]).transpose(2, 0, 1)).to_pickle(
            '{0}/b{1}_f(dis+gap).pickle'.format(base_dir, basket_len[-3]))
        pd.Panel(np.dstack(b2[1]).transpose(2, 1, 0)).to_pickle(
            '{0}/b{1}_t(dis).pickle'.format(base_dir, basket_len[-3]))
        pd.Panel(np.dstack(b3[0]).transpose(2, 0, 1)).to_pickle(
            '{0}/b{1}_f(dis+gap).pickle'.format(base_dir, basket_len[-4]))
        pd.Panel(np.dstack(b3[1]).transpose(2, 1, 0)).to_pickle(
            '{0}/b{1}_t(dis).pickle'.format(base_dir, basket_len[-4]))


class Plotter(object):
    def __init__(self, time_steps=1, which='v'):
        self._time_steps = time_steps
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(13, 5))
        plt.show()
        if which == 'v':
            plt.ylim((-5, 20))  # 4 predicting speed
        elif which == 'a':
            plt.ylim((-3.5, 3.5))  # 4 predicting acc
        elif which == 'displacement':
            plt.ylim((0, 3.5))
        self.plt_time = 0
        self.pred_to_plot = []
        self.road_ys_to_plot = []

    def update(self):
        if len(self.pred_to_plot) > 600:
            self.pred_to_plot = self.pred_to_plot[-600:]
            self.road_ys_to_plot = self.road_ys_to_plot[-600:]
        if not hasattr(self, 'pred_line'):
            self.pred_line, = plt.plot(
                np.arange(self.plt_time, self.plt_time+self._time_steps),
                self.pred_to_plot, 'b-', label='predict')
            self.road_line, = plt.plot(
                np.arange(self.plt_time, self.plt_time+self._time_steps),
                self.road_ys_to_plot, 'r-', label='real')
            plt.legend()
        else:
            self.pred_line.set_data(
                np.arange(self.plt_time+self._time_steps-len(self.pred_to_plot), self.plt_time+self._time_steps), self.pred_to_plot)
            self.road_line.set_data(
                np.arange(self.plt_time+self._time_steps-len(self.pred_to_plot), self.plt_time+self._time_steps), self.road_ys_to_plot)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.xlim((self.plt_time-600, self.plt_time+self._time_steps+10))
        plt.pause(0.0001)

    def append_data(self, pred, real):
        self.pred_to_plot += pred
        self.road_ys_to_plot += real


class RNN(object):

    def __init__(self, config, is_training):
        self._batch_size = config.batch_size
        self._time_steps = config.time_steps
        self._input_size = config.input_size
        self._output_size = config.output_size
        self._cell_layers = config.cell_layers
        self._cell_size = config.cell_size
        self._is_training = config.is_training
        self._weighted_cost = config.weighted_cost
        if not self._is_training:
            self._keep_prob = None
            self._lr = None
        else:
            self._keep_prob = config.keep_prob
            self._lr = config.learning_rate
            self._lr_decay_steps = config.decay_steps
            self._lr_decay_rate = config.decay_rate
        if not self._is_training:
            tf.reset_default_graph()
        self._built_RNN()
        self.saver = tf.train.Saver()
        self.sess = tf.Session()
        self.run(tf.initialize_all_variables())

    def _built_RNN(self):
        with tf.variable_scope('inputs'):
            self._xs = tf.placeholder(tf.float32, [self._batch_size, self._time_steps, self._input_size], name='xs')
            self._ys = tf.placeholder(tf.float32, [self._batch_size, self._time_steps, self._output_size], name='ys')
            if self._is_training:
                self._global_step = tf.placeholder(tf.int32, [], name='global_step')

        with tf.name_scope('RNN'):
            with tf.variable_scope('input_layer'):
                l_in_x = tf.reshape(self.xs, [-1, self._input_size], name='2_2D')  # (batch*n_step, in_size)
                # Ws (in_size, cell_size)
                Wi = self._weight_variable([self._input_size, self._cell_size])
                # bs (cell_size, )
                bi = self._bias_variable([self._cell_size, ])
                # l_in_y = (batch * n_steps, cell_size)
                with tf.name_scope('Wx_plus_b'):
                    l_in_y = tf.matmul(l_in_x, Wi) + bi
                with tf.name_scope('activation'):
                    l_in_y = tf.nn.relu(l_in_y)
                # reshape l_in_y ==> (batch, n_steps, cell_size)
                l_in_y = tf.reshape(l_in_y, [-1, self._time_steps, self._cell_size], name='2_3D')

            with tf.variable_scope('cell'):
                # cell = tf.nn.rnn_cell.BasicLSTMCell(self._cell_size, forget_bias=1.0, state_is_tuple=True)
                cell = tf.nn.rnn_cell.BasicRNNCell(self._cell_size)
                if self._cell_layers > 1:
                    cell = tf.nn.rnn_cell.MultiRNNCell([cell] * self._cell_layers, state_is_tuple=True)
                if self._is_training and self._keep_prob < 1:
                    cell = tf.nn.rnn_cell.DropoutWrapper(
                        cell,
                        input_keep_prob=1.,
                        output_keep_prob=self._keep_prob)
                with tf.name_scope('initial_state'):
                    self._cell_initial_state = cell.zero_state(self._batch_size, dtype=tf.float32)

                self.cell_outputs = []
                cell_state = self._cell_initial_state
                for t in range(self._time_steps):
                    if t > 0: tf.get_variable_scope().reuse_variables()
                    cell_output, cell_state = cell(l_in_y[:, t, :], cell_state)
                    self.cell_outputs.append(cell_output)
                self._cell_final_state = cell_state

            with tf.variable_scope('output_layer'):
                # cell_outputs_reshaped (BATCH*TIME_STEP, CELL_SIZE)
                cell_outputs_reshaped = tf.reshape(tf.concat(1, self.cell_outputs), [-1, self._cell_size])
                Wo = self._weight_variable((self._cell_size, self._output_size))
                bo = self._bias_variable((self._output_size,))
                product = tf.matmul(cell_outputs_reshaped, Wo) + bo
                # _pred shape (batch*time_step, output_size)
                self._pred = tf.nn.relu(product)    # for displacement

        with tf.name_scope('cost'):
            # # compute cost for the cell_outputs
            # loss_weights = tf.ones([self._batch_size*self._time_steps*self._output_size])
            # # compute cost for the cell_outputs
            # loss = tf.nn.seq2seq.sequence_loss(
            #     [tf.reshape(self._pred, [-1], name='reshape_pred')],
            #     [tf.reshape(self.ys, [-1], name='reshape_target')],
            #     [loss_weights],
            #     average_across_timesteps=False,
            #     average_across_batch=True,
            #     softmax_loss_function=self.ms_error,
            #     name='loss'
            # )
            # self._cost = loss
            _pred = tf.reshape(self._pred, [self._batch_size, self._time_steps, self._output_size])
            mse = self.ms_error(_pred, self._ys)
            mse_ave_across_batch = tf.reduce_mean(mse, 0)
            mse_sum_across_time = tf.reduce_sum(mse_ave_across_batch, 0)
            # mse_sum_across_outputs = tf.reduce_sum(mse_sum_across_time, 0)
            self._cost = mse_sum_across_time

        if self._is_training:
            with tf.name_scope('trian'):
                if self._lr_decay_rate < 1:
                    self._decay_lr = tf.train.exponential_decay(
                        self._lr, self._global_step,
                        self._lr_decay_steps, self._lr_decay_rate)
                else:
                    self._decay_lr = tf.convert_to_tensor(self._lr)
                self.train_op = tf.train.AdamOptimizer(self._decay_lr).minimize(self._cost)

    @property
    def lr(self):
        return self._decay_lr

    @property
    def cell_initial_state(self):
        return self._cell_initial_state

    @property
    def cell_final_state(self):
        return self._cell_final_state

    @property
    def global_step(self):
        return self._global_step

    @property
    def xs(self):
        return self._xs

    @property
    def ys(self):
        return self._ys

    @property
    def pred(self):
        return self._pred

    @property
    def cost(self):
        return self._cost

    @staticmethod
    def ms_error(y_pre, y_target):
        return tf.square(tf.sub(y_pre, y_target))

    @staticmethod
    def _weight_variable(shape, name='weights'):
        initializer = tf.random_normal_initializer(mean=0., stddev=0.5, )
        return tf.get_variable(shape=shape, initializer=initializer, name=name)

    @staticmethod
    def _bias_variable(shape, name='biases'):
        initializer = tf.constant_initializer(0.1)
        return tf.get_variable(name=name, shape=shape, initializer=initializer)

    def run(self, *args, **kwargs):
        return self.sess.run(*args, **kwargs)

    def save(self, path):
        return self.saver.save(self.sess, path, write_meta_graph=False)

    def restore(self, path):
        self.saver.restore(self.sess, path)

    def predict(self, inputs, is_initial_state):
        if is_initial_state:
            self.state_ = self.run(self.cell_initial_state)
        feed_dict = {self._xs: inputs, self._cell_initial_state: self.state_}
        pred, self.state_ = self.run([self._pred, self._cell_final_state], feed_dict=feed_dict)
        return pred[0, 0]


def test(model, test_config, id):
    plt.ion()
    model.restore(test_config.restore_path + '_' + test_config.predict)
    ps, vs, accs, dispms = test_config.data

    test_ps = ps.copy()
    test_vs = vs.copy()
    test_accs = accs.copy()
    test_dispms = dispms.copy()

    for i in range(1, test_config.sim_car_num):
        end_f_id = ps.iloc[:, i - 1].dropna().index[-1]    # for preceding vehicle
        is_initial_state = True
        init_counter = 0
        for t in ps.iloc[:, i].dropna().index:     # for current vehicle
            if t == end_f_id:
                # filter out the original value
                test_ps.loc[t + 1:, i] = None
                test_vs.loc[t + 1:, i] = None
                break
            # index from test data
            """if use the real ps and vs in here, the predicted acceleration is very close,
            but it has the accumulated error, which will result in a big change in position data.
            If use test_ps, and test_vs, which will depend on the data generated by last time (from prediction).
            the acceleration error will be greater then last method (using real data directly),
            but the position error will be less than last method."""
            if test_config.on_test:
                # depend on test
                p_data = test_ps.loc[t, i]
                dispms_data = test_dispms.loc[t, i]
            else:
                # depend on real
                p_data = ps.loc[t, i]
                dispms_data = dispms.loc[t, i]
            pl_data = ps.loc[t, i - 1]
            dx_data = pl_data - p_data

            if test_config.predict == 'displacement':
                input_data = np.asarray([
                    dispms_data * test_config.displacement_scale + test_config.displacement_bias,  # displacement
                    dx_data * test_config.gap_scale + test_config.gap_bias,  # gap
                ])[np.newaxis, np.newaxis, :]

                new_displacement = model.predict(input_data, is_initial_state)
                if new_displacement >= 0:
                    # start to have proceeding condition
                    new_displacement = 0 if new_displacement < 0 else new_displacement
                    test_ps.loc[t + 1, i] = test_ps.loc[t, i] + new_displacement
                    test_dispms.loc[t + 1, i] = new_displacement
                    if is_initial_state:
                        # filter out the original value
                        test_ps.loc[:t, i] = None
                        test_vs.loc[:t, i] = None
                    is_initial_state = False

            else:
                raise ValueError('not support')

    plt.style.use('classic')
    predict = 'disp'
    model_name = 'RNN{0}({1:.1f})'.format(predict, train_config.time_steps)
    base_dir = 'RNN%s(%s)/' % (predict, train_config.time_steps / 10)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ps.index /= 10
    test_ps.index /= 10
    ax.plot(ps, 'k-', label='$I-80$')
    ax.plot(test_ps.iloc[:, 1:], 'r--', label='${}$'.format(model_name))
    fig.suptitle('$Simulate\ trajectory\ on\ %s\ data$' % 'predicted')
    ax.set_xlabel('$Time\ (s)$')
    ax.set_ylabel('$Position\ (m)$')
    for i in range(1, test_config.sim_car_num):
        traj = ps.iloc[:, i].dropna()
        x = traj.index[0]
        y = traj.iloc[0]
        ax.text(x - 1, y - 13, '$f{}$'.format(i))
    handles, labels = ax.get_legend_handles_labels()
    plt.legend([handles[0], handles[-1]], [labels[0], labels[-1]], loc='best')
    plt.ylim((0, 400))
    plt.savefig(base_dir + 'RNN%s_traj.png' % (predict), format='png', dpi=1000)

    # f, ax = plt.subplots(8, 1)
    # f.suptitle('Velocity')
    # for i in range(8):
    #     ax[i].plot(vs.iloc[:, i + 1], 'k-')
    #     ax[i].plot(test_vs.iloc[:, i + 1], 'r--')
    #
    # f, ax = plt.subplots(8, 1)
    # f.suptitle('Acceleration')
    # for i in range(8):
    #     ax[i].plot(accs.iloc[:, i + 1], 'k-')
    #     ax[i].plot(test_accs.iloc[:, i + 1], 'r--')
    #
    # f, ax = plt.subplots(8, 1)
    # f.suptitle('test real acceleration diff cumsum')
    # for i in range(8):
    #     ax[i].plot((test_accs.iloc[:, i + 1] - accs.iloc[:, i + 1]).cumsum(), 'k-')

    plt.show()


def train(train_config, test_config):
    # plotter = Plotter(train_config.time_steps, train_config.predict)
    data = RNNDataSet()
    data.normalize(train_config)        # normalization
    train_rnn = RNN(train_config, is_training=True)
    # merged = tf.merge_all_summaries()
    # writer = tf.train.SummaryWriter("logs/", train_rnn.sess.graph)
    # test_rnn = RNN(test_config, is_training=False)
    for i in range(train_config.iter_steps):
        b_xs, b_ys, zero_initial_state = data.next(train_config.batch_size, train_config.time_steps)  # this for a batch
        if zero_initial_state:
            state_ = train_rnn.run(train_rnn.cell_initial_state)
        feed_dict = {train_rnn.xs: b_xs, train_rnn.ys: b_ys, train_rnn.cell_initial_state: state_, train_rnn.global_step: i}
        _, state_, cost_, lr_, pred_ = train_rnn.run([train_rnn.train_op, train_rnn.cell_final_state, train_rnn.cost, train_rnn.lr, train_rnn.pred],
                                          feed_dict=feed_dict)
        # res_pred = pred_[:train_config.time_steps, 0].flatten()
        # res_real = b_ys[0, :, 0].flatten()
        # plotter.append_data(res_pred.tolist(), res_real.tolist())

        # a = tf.get_default_graph().get_tensor_by_name(
        #     "trian/gradients/cost/Square_grad/mul" + ":0")
        # a = tf.Print(a, [a], message="This is a: ")
        # b = train_rnn.run(a, feed_dict=feed_dict)
        # print(b, '    cost for all time: ',cost_)
        # exit()

        if i % train_config.plot_loop == 0:
            # plotter.update()
            print('step:', i, 'cost: ', cost_, 'lr: ', lr_)
            print("Save to path: ", train_rnn.save('tmp/rnn_{}'.format(train_config.predict)))
            # test(test_rnn, test_config, 890)
            # plt.pause(0.001)
            # print('done plot')
        # plotter.plt_time += train_config.time_steps



class TrainConfig(object):
    # 0400-0415: much oscillation occurs on lane 2,4,5,6
    # data_path = 'datasets/I80-0400-0415-filter_0.8_gap_displacement.pickle'

    # 0500-0515: much oscillation occurs on lane 2,3,4,5,6
    data_path = 'datasets/I80-0500-0515-filter_0.8_T_v_ldxdvhdisplace.pickle'

    # data_path = 'datasets/I80-0400_lane2.pickle'
    iter_steps = 50001
    plot_loop = 5000
    basket_len = [40, 100, 300, 1000]
    predict = 'displacement'
    batch_size = 32
    time_steps = 10
    input_size = 2
    output_size = 1
    cell_layers = 1
    cell_size = 20
    displacement_scale = 1 / 3.5
    displacement_bias = - 0.5
    gap_scale = 1 / 86
    gap_bias = -0.5
    is_training = True
    weighted_cost = False       # latest step has higher weight
    keep_prob = 1
    learning_rate = 3e-4
    decay_steps = 10000          # lr * decay_rate ^ (1/decay_steps)
    decay_rate = 0.9


class TestConfig(object):
    data_path = 'datasets/I80-0400_lane2.pickle'
    predict = 'displacement'
    batch_size = 1
    time_steps = 1
    input_size = 2
    output_size = 1
    cell_layers = 1
    cell_size = 20
    displacement_scale = 1 / 3.5
    displacement_bias = - 0.5
    gap_scale = 1 / 86
    gap_bias = -0.5
    is_training = False
    weighted_cost = True
    on_test = True
    restore_path = 'tmp/rnn'
    sim_car_num = 9
    start_car_id = 890

    def __init__(self):
        self.data = self.get_test_date()

    def get_test_date(self):
        df = pd.read_pickle(self.data_path)[['filter_position', 'Vehicle_ID', 'Frame_ID', 'displacement',
                                             'deri_v', 'deri_a_clipped']].dropna().astype(np.float32)
        df = df[df['filter_position'] < 380]
        ids = np.unique(df.Vehicle_ID)
        filter_ids = ids[ids >= self.start_car_id]
        ps = pd.DataFrame()
        vs = pd.DataFrame()
        accs = pd.DataFrame()
        dispms = pd.DataFrame()
        for i, car_id in enumerate(filter_ids):
            if i >= self.sim_car_num:
                break
            car_data = df[df['Vehicle_ID'] == car_id]
            car_data = car_data.set_index(['Frame_ID'])
            car_position = car_data['filter_position']
            car_speed = car_data['deri_v']
            car_acc = car_data['deri_a_clipped']
            car_dispms = car_data['displacement']
            # shape (time, n_car) for positions
            ps = pd.concat([ps, car_position.rename(i)], axis=1)
            # shape (time, n_car) for speeds
            vs = pd.concat([vs, car_speed.rename(i)], axis=1)
            accs = pd.concat([accs, car_acc.rename(i)], axis=1)
            dispms = pd.concat([dispms, car_dispms.rename(i)], axis=1)
        return [ps, vs, accs, dispms]


def set_seed(seed):
    tf.set_random_seed(seed)
    np.random.seed(seed)

if __name__ == '__main__':
    """
        For this model
        Input: my displacement, gap;
        Output: my next displacement.
    """
    set_seed(1)

    train_config = TrainConfig()
    test_config = TestConfig()

    ###################################
    # re-organize RNN data
    # data = DataSet('datasets/I80-0500-0515-filter_0.8_T_v_ldxdvhdisplace_proposition&displacement.pickle')   # un batched data
    # data.put_in_basket(basket_len=train_config.basket_len)
    ###################################

    # TODO: set the output as next input sep2sep model: https://github.com/tensorflow/tensorflow/blob/master/tensorflow/models/rnn/translate/seq2seq_model.py
    # https://www.tensorflow.org/versions/r0.11/tutorials/seq2seq/index.html
    # train(train_config, test_config)

    test_rnn = RNN(test_config, is_training=False)
    test(test_rnn, test_config, id=890)
from Agents import modelFreeAgent
import numpy as np
from collections import deque
import random
import joblib


class DeepQ(modelFreeAgent.ModelFreeAgent):
    displayName = 'Deep Q'
    newParameters = [modelFreeAgent.ModelFreeAgent.Parameter('Batch Size', 1, 256, 1, 32, True, True, "The number of transitions to consider simultaneously when updating the agent"),
                     modelFreeAgent.ModelFreeAgent.Parameter('Memory Size', 1, 655360, 1, 1000, True, True, "The maximum number of timestep transitions to keep stored"),
                     modelFreeAgent.ModelFreeAgent.Parameter('Target Update Interval', 1, 100000, 1, 200, True, True, "The distance in timesteps between target model updates")]
    parameters = modelFreeAgent.ModelFreeAgent.parameters + newParameters

    def __init__(self, *args):
        paramLen = len(DeepQ.newParameters)
        super().__init__(*args[:-paramLen])
        self.batch_size, self.memory_size, self.target_update_interval = [int(arg) for arg in args[-paramLen:]]
        self.model = self.buildQNetwork()
        self.target = self.buildQNetwork()
        self.memory = deque(maxlen=self.memory_size)
        self.total_steps = 0
        self.allMask = np.full((1, self.action_size), 1)
        self.allBatchMask = np.full((self.batch_size, self.action_size), 1)

    def choose_action(self, state):
        qval = self.predict(state, False)
        epsilon = self.min_epsilon + (self.max_epsilon - self.min_epsilon) * np.exp(-self.decay_rate * self.time_steps)
        # TODO: Put epsilon at a level near this
        # if random.random() > epsilon:
        action = np.argmax(qval)
        # else:
            # action = self.state_size.sample()
        return action

    def sample(self):
        return random.sample(self.memory, self.batch_size)

    def addToMemory(self, state, action, reward, new_state, done):
        self.memory.append((state, action, reward, new_state, done))

    def remember(self, state, action, reward, new_state, done=False):
        self.addToMemory(state, action, reward, new_state, done)
        loss = 0
        if len(self.memory) < 2*self.batch_size:
            return loss
        mini_batch = self.sample()

        X_train, Y_train = self.calculateTargetValues(mini_batch)
        loss = self.model.train_on_batch(X_train, Y_train)
        self.updateTarget()
        return loss

    def updateTarget(self):
        if self.total_steps >= 2*self.batch_size and self.total_steps % self.target_update_interval == 0:
            self.target.set_weights(self.model.get_weights())
            print("target updated")
        self.total_steps += 1

    def predict(self, state, isTarget):
        import tensorflow as tf

        shape = (1,) + self.state_size
        state = np.reshape(state, shape)
        if isTarget:
            result = self.target.predict([state, self.allMask])
        else:
            result = self.model.predict([state, self.allMask])
        return result

    def update(self):
        pass

    def reset(self):
        pass

    def create_one_hot(self, vector_length, hot_index):
        output = np.zeros((vector_length))
        if hot_index != -1:
            output[hot_index] = 1
        return output

    def buildQNetwork(self):
        from tensorflow.python.keras.optimizer_v2.adam import Adam
        from tensorflow.keras.models import Model
        from tensorflow.keras.layers import Dense, Input, Flatten, multiply

        inputA = Input(shape=self.state_size)
        inputB = Input(shape=(self.action_size,))
        x = Flatten()(inputA)
        x = Dense(24, input_dim=self.state_size, activation='relu')(x)  # fully connected
        x = Dense(24, activation='relu')(x)
        x = Dense(self.action_size, activation='linear')(x)
        outputs = multiply([x, inputB])
        model = Model(inputs=[inputA, inputB], outputs=outputs)
        model.compile(loss='mse', optimizer=Adam(lr=0.001))
        return model

    def calculateTargetValues(self, mini_batch):
        X_train = [np.zeros((self.batch_size,) + self.state_size), np.zeros((self.batch_size,) + (self.action_size,))]
        next_states = np.zeros((self.batch_size,) + self.state_size)

        for index_rep, (state, action, reward, next_state, isDone) in enumerate(mini_batch):
            X_train[0][index_rep] = state
            X_train[1][index_rep] = self.create_one_hot(self.action_size, action)
            next_states[index_rep] = next_state

        Y_train = np.zeros((self.batch_size,) + (self.action_size,))
        qnext = self.target.predict([next_states, self.allBatchMask])
        qnext = np.amax(qnext, 1)

        for index_rep, (state, action, reward, next_state, isDone) in enumerate(mini_batch):
            if isDone:
                Y_train[index_rep][action] = reward
            else:
                Y_train[index_rep][action] = reward + qnext[index_rep] * self.gamma
        return X_train, Y_train

    def __deepcopy__(self, memodict={}):
        pass

    def save(self, filename):
        mem = self.model.get_weights()
        joblib.dump((DeepQ.displayName, mem), filename)

    def load(self, filename):
        name, mem = joblib.load(filename)
        if name != DeepQ.displayName:
            print('load failed')
        else:
            self.model.set_weights(mem)
            self.target.set_weights(mem)

    def memsave(self):
        return self.model.get_weights()

    def memload(self, mem):
        self.model.set_weights(mem)
        self.target.set_weights(mem)
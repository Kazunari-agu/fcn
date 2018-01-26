import os.path as osp
import numpy as np

import chainer
import chainer.functions as F
import chainer.links as L

from weight import UpsamplingDeconvWeight


class FCN32s(chainer.Chain):
    def __init__(self, n_class=38):
        self.n_class = n_class
        kwargs ={
            'initialW': chainer.initializers.Zero(),
            'initial_bias': chainer.initializers.Zero(),
        }
        super(FCN32s, self).__init__()
        with self.init_scope():
            self.conv1_1 = L.Convolution2D(3, 64, 3, 1, 100, **kwargs)
            self.conv1_2 = L.Convolution2D(64, 64, 3, 1, 1, **kwargs)

            self.conv2_1 = L.Convolution2D(64, 128, 3, 1, 1, **kwargs)
            self.conv2_2 = L.Convolution2D(128, 128, 3, 1, 1, **kwargs)

            self.conv3_1 = L.Convolution2D(128, 256, 3, 1, 1, **kwargs)
            self.conv3_2 = L.Convolution2D(256, 256, 3, 1, 1, **kwargs)
            self.conv3_3 = L.Convolution2D(256, 256, 3, 1, 1, **kwargs)

            self.conv4_1 = L.Convolution2D(256, 512, 3, 1, 1, **kwargs)
            self.conv4_2 = L.Convolution2D(512, 512, 3, 1, 1, **kwargs)
            self.conv4_3 = L.Convolution2D(512, 512, 3, 1, 1, **kwargs)

            self.conv5_1 = L.Convolution2D(512, 512, 3, 1, 1, **kwargs)
            self.conv5_2 = L.Convolution2D(512, 512, 3, 1, 1, **kwargs)
            self.conv5_3 = L.Convolution2D(512, 512, 3, 1, 1, **kwargs)

            self.fc6 = L.Convolution2D(512, 4096, 7, 1, 0, **kwargs)
            self.fc7 = L.Convolution2D(4096, 4096, 1, 1, 0, **kwargs)

            self.score_fr= L.Convolution2D(4096, n_class, 1, 1, 0, **kwargs)

            self.upscore = L.Deconvolution2D(n_class, n_class, 64, 32, 0, nobias=True, initialW=UpsamplingDeconvWeight())



    def __call__(self, x, t=None, train=False, test=False):
        h = x
        h = F.relu(self.conv1_1(h))
        h = F.relu(self.conv1_2(h))
        h = F.max_pooling_2d(h, 2, stride=2)
        #print("pool1: ", h.shape)
        #print(h.shape)

        h = F.relu(self.conv2_1(h))
        h = F.relu(self.conv2_2(h))
        h = F.max_pooling_2d(h, 2, stride=2)
        #print("pool2: ", h.shape)
        #print(h.shape)

        h = F.relu(self.conv3_1(h))
        h = F.relu(self.conv3_2(h))
        h = F.relu(self.conv3_3(h))
        h = F.max_pooling_2d(h, 2, stride=2)
        #print("pool3: ", h.shape)
        #print(h.shape)

        h = F.relu(self.conv4_1(h))
        h = F.relu(self.conv4_2(h))
        h = F.relu(self.conv4_3(h))
        h = F.max_pooling_2d(h, 2, stride=2)
        #print("pool4: ", h.shape)
        #print(h.shape)

        h = F.relu(self.conv5_1(h))
        h = F.relu(self.conv5_2(h))
        h = F.relu(self.conv5_3(h))
        h = F.max_pooling_2d(h, 2, stride=2)
        #print("pool5: ", h.shape)
        #print(h.shape)

        h = F.dropout(F.relu(self.fc6(h)), ratio=.5)
        #print("fc6: ", h.shape)
        #print(h.shape)
        h = F.dropout(F.relu(self.fc7(h)), ratio=.5)
        #print("fc7: ", h.shape)
        #print(h.shape)

        h = self.score_fr(h)
        #print("score_fr: ", h.shape)
        #print(h.shape)


        h = self.upscore(h)
        #print("upscore: ", h.shape)
        #print(h.shape)
        h = h[:,:, 19:19 + x.data.shape[2], 19:19 + x.data.shape[3]]
        #print("reshape: ", h.shape)

        score = h
        self.score = h

        if t is None:
            assert not chainer.config.train
            return

        if train:
            self.loss = F.softmax_cross_entropy(self.score, t, normalize=False)
            self.accuracy = F.accuracy(self.score, t)
            return self.loss, self.accuracy
        else:
            pred = F.softmax(score)
            return pred

    def init_from_vgg16(self, vgg16):
        for l in self.children():
            if l.name.startswith('conv'):
                l1 = getattr(vgg16, l.name)
                l2 = getattr(self, l.name)
                assert l1.W.shape == l2.W.shape
                assert l1.b.shape == l2.b.shape
                l2.W.data[...] = l1.W.data[...]
                l2.b.data[...] = l1.b.data[...]

                #print(l.name + "was copied to new model from vgg16")

    def predict(self, imgs):
        lbls = []
        for img in imgs:
             with chainer.no_backprop_mode(), chainer.using_config('train', False):
                 x = np.asarray(img[None])
                 self.__call__(x)
                 lbl = chainer.functions.argmax(self.score, axis=1)

             lbl = chainer.cuda.to_cpu(lbl.array[0])
             lbls.append(lbl)

        return lbls

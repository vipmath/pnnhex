
import tensorflow as tf

class Layer(object):
    
    def __init__(self, layer_name, paddingMethod="SAME", reuse_var=False):
        self.layer_name = layer_name
        self.paddingMethod=paddingMethod
        self.reuse_var=reuse_var

    # padding="SAME" or "VALID"
    def _conv2d(self, input_tensor, weight_shape, bias_shape):
        
        self.weight = tf.get_variable("weight", weight_shape, initializer=tf.truncated_normal_initializer(stddev=0.1))
        
        self.bias = tf.get_variable("bias", bias_shape, initializer=tf.constant_initializer(0.0))
        
        conv = tf.nn.conv2d(input_tensor, self.weight, strides=[1, 1, 1, 1], padding=self.paddingMethod)
        
        return (conv + self.bias)

    def _relu(self, input_tensor):
        return tf.nn.relu(input_tensor)

    def convolve(self, input_tensor, weight_shape, bias_shape):
        with tf.variable_scope(self.layer_name) as sp:
            if self.reuse_var:
                sp.reuse_variables()
            relu=self._relu(self._conv2d(input_tensor, weight_shape, bias_shape))
            return relu

    def convolve_no_relu(self, input_tensor, weight_shape, bias_shape):
        with tf.variable_scope(self.layer_name) as sp:
            if self.reuse_var:
                sp.reuse_variables()
            return self._conv2d(input_tensor, weight_shape, bias_shape)

    #logits for move prediction
    def move_logits(self, input_tensor, boardsize):
        with tf.variable_scope(self.layer_name) as sp:
            if self.reuse_var:
                sp.reuse_variables()
            return self._one_filter_out(input_tensor, boardsize)

    # input batchsize x BOARDSIZE x BOARDSIZE x DEPTH
    def _one_filter_out(self, input_tensor, boardsize):
        input_shape = input_tensor.get_shape()
        batch_size = input_shape[0].value
        assert(input_shape[1] == boardsize)
        assert(input_shape[2] == boardsize)
        weight_shape = (1, 1, input_shape[3], 1)
        bias_shape = (boardsize * boardsize)
        
        self.weight = tf.get_variable("output_layer_weight", weight_shape,
                                      initializer=tf.truncated_normal_initializer(stddev=0.1))
        self.bias = tf.get_variable("position_bias", bias_shape, initializer=tf.constant_initializer(0.0))
        
        out = tf.nn.conv2d(input_tensor, self.weight, strides=[1, 1, 1, 1], padding="SAME")
        logits = tf.reshape(out, shape=(batch_size, boardsize * boardsize)) + self.bias
        
        return logits
    
        
if __name__ == "__main__":
    sess = tf.InteractiveSession()
    conv1 = Layer("layer1")
    # x_in=tf.placeholder(dtype=tf.float32, shape=[1,227,227,3])
    x_in = tf.Variable(tf.random_normal([1, 227, 227, 3]))
    out = conv1.convolve(x_in, weight_shape=[11, 11, 3, 96], bias_shape=[96])

    print(out)
    print(out.get_shape())
    sp = out.get_shape()
    print(sp[2])


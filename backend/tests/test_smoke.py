import tensorflow as tf

from app.config import STUDENT_PATH, TEACHER_PATH
from app.eqt_layers import CUSTOM_OBJECTS


def test_teacher_loads_with_vendored_layers():
    model = tf.keras.models.load_model(TEACHER_PATH, custom_objects=CUSTOM_OBJECTS, compile=False)
    assert model.input_shape == (None, 6000, 3)
    assert len(model.outputs) == 3


def test_student_loads():
    model = tf.keras.models.load_model(STUDENT_PATH, compile=False)
    assert model.input_shape == (None, 6000, 3)
    assert model.count_params() == 60659

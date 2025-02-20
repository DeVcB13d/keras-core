import os
import zipfile

from absl import logging

from keras_core.api_export import keras_core_export
from keras_core.legacy.saving import legacy_h5_format
from keras_core.saving import saving_lib
from keras_core.utils import file_utils
from keras_core.utils import io_utils

try:
    import h5py
except ImportError:
    h5py = None


@keras_core_export(
    ["keras_core.saving.save_model", "keras_core.models.save_model"]
)
def save_model(model, filepath, overwrite=True, **kwargs):
    """Saves a model as a `.keras` file.

    Args:
        model: Keras model instance to be saved.
        filepath: `str` or `pathlib.Path` object. Path where to save the model.
        overwrite: Whether we should overwrite any existing model at the target
            location, or instead ask the user via an interactive prompt.

    Example:

    ```python
    model = keras_core.Sequential(
        [
            keras_core.layers.Dense(5, input_shape=(3,)),
            keras_core.layers.Softmax(),
        ],
    )
    model.save("model.keras")
    loaded_model = keras_core.saving.load_model("model.keras")
    x = keras.random.uniform((10, 3))
    assert np.allclose(model.predict(x), loaded_model.predict(x))
    ```

    Note that `model.save()` is an alias for `keras_core.saving.save_model()`.

    The saved `.keras` file contains:

    - The model's configuration (architecture)
    - The model's weights
    - The model's optimizer's state (if any)

    Thus models can be reinstantiated in the exact same state.
    """
    include_optimizer = kwargs.pop("include_optimizer", True)
    save_format = kwargs.pop("save_format", False)
    if save_format:
        if str(filepath).endswith((".h5", ".hdf5")) or str(filepath).endswith(
            ".keras"
        ):
            logging.warning(
                "The `save_format` argument is deprecated in Keras Core. "
                "We recommend removing this argument as it can be inferred "
                "from the file path. "
                f"Received: save_format={save_format}"
            )
        else:
            raise ValueError(
                "The `save_format` argument is deprecated in Keras Core. "
                "Please remove this argument and pass a file path with "
                "either `.keras` or `.h5` extension."
                f"Received: save_format={save_format}"
            )
    if kwargs:
        raise ValueError(
            "The following argument(s) are not supported: "
            f"{list(kwargs.keys())}"
        )

    # Deprecation warnings
    if str(filepath).endswith((".h5", ".hdf5")):
        logging.warning(
            "You are saving your model as an HDF5 file via `model.save()`. "
            "This file format is considered legacy. "
            "We recommend using instead the native Keras format, "
            "e.g. `model.save('my_model.keras')`."
        )

    if str(filepath).endswith(".keras"):
        # If file exists and should not be overwritten.
        try:
            exists = os.path.exists(filepath)
        except TypeError:
            exists = False
        if exists and not overwrite:
            proceed = io_utils.ask_to_proceed_with_overwrite(filepath)
            if not proceed:
                return
        saving_lib.save_model(model, filepath)
    elif str(filepath).endswith((".h5", ".hdf5")):
        legacy_h5_format.save_model_to_hdf5(
            model, filepath, overwrite, include_optimizer
        )
    else:
        raise ValueError(
            "Invalid filepath extension for saving. "
            "Please add either a `.keras` extension for the native Keras "
            f"format (recommended) or a `.h5` extension. "
            "Use `tf.saved_model.save()` if you want to export a SavedModel "
            "for use with TFLite/TFServing/etc. "
            f"Received: filepath={filepath}."
        )


@keras_core_export(
    ["keras_core.saving.load_model", "keras_core.models.load_model"]
)
def load_model(filepath, custom_objects=None, compile=True, safe_mode=True):
    """Loads a model saved via `model.save()`.

    Args:
        filepath: `str` or `pathlib.Path` object, path to the saved model file.
        custom_objects: Optional dictionary mapping names
            (strings) to custom classes or functions to be
            considered during deserialization.
        compile: Boolean, whether to compile the model after loading.
        safe_mode: Boolean, whether to disallow unsafe `lambda` deserialization.
            When `safe_mode=False`, loading an object has the potential to
            trigger arbitrary code execution. This argument is only
            applicable to the Keras v3 model format. Defaults to True.

    Returns:
        A Keras model instance. If the original model was compiled,
        and the argument `compile=True` is set, then the returned model
        will be compiled. Otherwise, the model will be left uncompiled.

    Example:

    ```python
    model = keras_core.Sequential([
        keras_core.layers.Dense(5, input_shape=(3,)),
        keras_core.layers.Softmax()])
    model.save("model.keras")
    loaded_model = keras_core.saving.load_model("model.keras")
    x = np.random.random((10, 3))
    assert np.allclose(model.predict(x), loaded_model.predict(x))
    ```

    Note that the model variables may have different name values
    (`var.name` property, e.g. `"dense_1/kernel:0"`) after being reloaded.
    It is recommended that you use layer attributes to
    access specific variables, e.g. `model.get_layer("dense_1").kernel`.
    """
    is_keras_zip = str(filepath).endswith(".keras") and zipfile.is_zipfile(
        filepath
    )

    # Support for remote zip files
    if (
        file_utils.is_remote_path(filepath)
        and not file_utils.isdir(filepath)
        and not is_keras_zip
    ):
        local_path = os.path.join(
            saving_lib.get_temp_dir(), os.path.basename(filepath)
        )

        # Copy from remote to temporary local directory
        file_utils.copy(filepath, local_path, overwrite=True)

        # Switch filepath to local zipfile for loading model
        if zipfile.is_zipfile(local_path):
            filepath = local_path
            is_keras_zip = True

    if is_keras_zip:
        return saving_lib.load_model(
            filepath,
            custom_objects=custom_objects,
            compile=compile,
            safe_mode=safe_mode,
        )
    if str(filepath).endswith((".h5", ".hdf5")):
        return legacy_h5_format.load_model_from_hdf5(filepath)
    elif str(filepath).endswith(".keras"):
        raise ValueError(
            f"File not found: filepath={filepath}. "
            "Please ensure the file is an accessible `.keras` "
            "zip file."
        )
    else:
        raise ValueError(
            f"File format not supported: filepath={filepath}. "
            "Keras Core only supports V3 `.keras` files and "
            "legacy H5 format files (`.h5` extension). "
            "Note that the legacy SavedModel format is not "
            "supported in Keras Core."
        )


def load_weights(model, filepath, skip_mismatch=False, **kwargs):
    if str(filepath).endswith(".keras"):
        if kwargs:
            raise ValueError(f"Invalid keyword arguments: {kwargs}")
        saving_lib.load_weights_only(
            model, filepath, skip_mismatch=skip_mismatch
        )
    elif str(filepath).endswith(".weights.h5"):
        if kwargs:
            raise ValueError(f"Invalid keyword arguments: {kwargs}")
        saving_lib.load_weights_only(
            model, filepath, skip_mismatch=skip_mismatch
        )
    elif str(filepath).endswith(".h5") or str(filepath).endswith(".hdf5"):
        by_name = kwargs.pop("by_name", False)
        if kwargs:
            raise ValueError(f"Invalid keyword arguments: {kwargs}")
        if not h5py:
            raise ImportError(
                "Loading a H5 file requires `h5py` to be installed."
            )
        with h5py.File(filepath, "r") as f:
            if "layer_names" not in f.attrs and "model_weights" in f:
                f = f["model_weights"]
            if by_name:
                legacy_h5_format.load_weights_from_hdf5_group_by_name(
                    f, model, skip_mismatch
                )
            else:
                legacy_h5_format.load_weights_from_hdf5_group(f, model)
    else:
        raise ValueError(
            f"File format not supported: filepath={filepath}. "
            "Keras Core only supports V3 `.keras` and `.weights.h5` "
            "files."
        )

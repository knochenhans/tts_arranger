import os
import tempfile
import ffmpeg  # type: ignore
import numpy as np
import scipy  # type: ignore
import loguru


class AudioWriter:
    def write(
        self, numpy_segment: np.ndarray, output_filename: str, sample_rate: int
    ) -> None:
        """
        Compress, convert and write numpy array as a given output file path and name

        :param segment: numpy array to be written
        :type segment: np.ndarray

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        # Set default format to mp3
        output_format = os.path.splitext(output_filename)[1][1:] or "mp3"

        folder = os.path.dirname(os.path.abspath(output_filename))

        os.makedirs(folder, exist_ok=True)

        # Ensure output file name has a file extension
        output_filename = os.path.splitext(output_filename)[0] + "." + output_format

        loguru.logger.info(f"Compressing, converting and saving as {output_filename}.")

        output_args = {}

        if output_format == "mp3":
            output_args["audio_bitrate"] = "320k"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "temp")
            scipy.io.wavfile.write(temp_path, sample_rate, numpy_segment)

            # comp_expansion = 12.5
            # comp_raise = 0.0001

            # Convert to target format
            (
                ffmpeg.input(temp_path)
                # .filter("speechnorm", e=f"{comp_expansion}", r=f"{comp_raise}", l=1)
                .output(output_filename, **output_args, loglevel="error").run(
                    overwrite_output=True
                )
            )

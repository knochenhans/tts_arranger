import datetime
import math
import os
import subprocess
import tempfile
from pathvalidate import sanitize_filename

import ffmpeg  # type: ignore
from PIL import Image  # type: ignore
from loguru import logger
import srt  # type: ignore


class FFmpegProcessor:
    def __init__(
        self, temp_files, chapter_times, item_data, project_path, output_format
    ):
        self.temp_files = temp_files
        self.chapter_times = chapter_times
        self.item_data = item_data
        self.project_path = project_path
        self.output_format = output_format

    def _remove_last_arg(self, cmd: list[str], arg: str) -> list[str]:
        if cmd:
            cmd.reverse()
            index = cmd.index(arg)
            if index:
                cmd.pop(index - 1)
                cmd.pop(index - 1)
            cmd.reverse()
        return cmd

    def _add_image(self, image: Image.Image, input_file: str, output_file: str) -> None:
        image_width, image_height = image.size

        with tempfile.TemporaryDirectory() as temp_dir:
            audio = ffmpeg.input(input_file)["a"]
            image_format = "jpeg"
            image_path = os.path.join(temp_dir, f"tts_image.{image_format}")

            if image.format == "PNG" and image.mode != "RGBA":
                image = image.convert("RGBA")
                background = Image.new("RGBA", image.size, (255, 255, 255))
                image = Image.alpha_composite(background, image)

            if image.mode != "RGB":
                image = image.convert("RGB")

            image.crop(
                (0, 0, math.ceil(image_width / 2) * 2, math.ceil(image_height / 2) * 2)
            ).save(image_path, format=image_format, quality=90)

            cover = ffmpeg.input(image_path)["v"]

            (
                ffmpeg.output(
                    audio,
                    cover,
                    output_file,
                    vcodec="copy",
                    acodec="copy",
                    map_metadata=0,
                    **{"disposition:v:0": "attached_pic"},
                    loglevel="error",
                ).run(overwrite_output=True)
            )

    def process_ffmpeg(self, project, title, temp_dir, subtitles):
        if len(self.temp_files) > 0:
            metadata_lines = [";FFMETADATA1\n"]

            for c, chapter in enumerate(project["chapters"]):
                chapter_times = self.chapter_times[c]
                chapter_title = chapter.get("title", f"Chapter {c + 1}")
                metadata_lines.append(
                    f"[CHAPTER]\nSTART={chapter_times[0]}\nEND={chapter_times[1]}\ntitle={chapter_title}\n"
                )

            metadata = "".join(metadata_lines)
            metadata_filename = os.path.join(temp_dir, "metadata")

            with open(metadata_filename, "w", encoding="utf-8") as metadata_file:
                metadata_file.write(metadata)

            if title == "":
                title = project.get("title", "Untitled Project")

            output_filename = os.path.join(self.project_path, sanitize_filename(title))
            output_extension = f".{self.output_format}"
            output_filename = output_filename[: 255 - len(output_extension)]
            output_path = output_filename + output_extension
            output_files = []

            os.makedirs(self.project_path, exist_ok=True)
            infiles = [ffmpeg.input(file) for _, file in self.temp_files]
            metadata_input = ffmpeg.input(metadata_filename)

            if self.output_format not in ["m4b", "m4a"]:
                logger.warning("Chapters are only possible for m4b/m4a at the moment.")

            project_title = project.get("title", "TTS Project")
            project_subtitle = project.get("subtitle", "")
            project_author = project.get("author", "")

            cmd = (
                ffmpeg.concat(*infiles, v=0, a=1)
                .output(
                    metadata_input,
                    output_path,
                    map_metadata=1,
                    **{
                        "metadata": f"title={project_title}",
                        "metadata:": f"album={project_subtitle}",
                        "metadata:g": f"artist={project_author}",
                    },
                    loglevel="error",
                )
                .compile(overwrite_output=True)
            )

            cmd = self._remove_last_arg(cmd, "-map")
            subprocess.call(cmd)
            output_files.append(output_path)

            logger.success(
                f'Synthesizing project "{project_title}" finished, file saved as "{output_path}".'
            )

            if "cover_image" in project:
                try:
                    with Image.open(project["cover_image"]) as image:
                        if image.format:
                            image_added = False

                            for output_file in output_files:
                                output_path_with_image = (
                                    output_file + "_tmp" + output_extension
                                )
                                self._add_image(
                                    image, output_file, output_path_with_image
                                )
                                os.remove(output_file)
                                os.rename(output_path_with_image, output_file)
                                image_added = True

                            if image_added:
                                logger.success(
                                    "Project image added to final output for all files."
                                )

                except Image.UnidentifiedImageError:
                    logger.error(
                        "Could not add image to final output, image file is not a valid image file."
                    )

            if subtitles:
                srt_output_file = os.path.splitext(output_path)[0] + ".srt"
                srt_data = []
                start_time = 0

                for i, segment_data in enumerate(self.item_data):
                    segment_length = segment_data[0] / 1000
                    segment_data_str = segment_data[1].strip()

                    if segment_data_str != "":
                        subtile_data = srt.Subtitle(
                            index=i + 1,
                            start=srt.timedelta(microseconds=start_time),
                            end=srt.timedelta(microseconds=start_time + segment_length),
                            content=segment_data_str,
                        )
                        srt_data.append(subtile_data)

                    start_time += segment_length

                logger.info(f"Writing SRT to {srt_output_file}")

                with open(srt_output_file, "w", encoding="utf-8") as srt_file:
                    srt_file.write(srt.compose(srt_data))

            probe = ffmpeg.probe(output_path)
            duration = float(probe["format"]["duration"])
            total_duration = str(datetime.timedelta(seconds=int(duration)))
            logger.info(f"Total duration: {total_duration}")
            logger.info(f"Output file: {output_path}")
            logger.info(f"Chapter count: {len(project['chapters'])}")
            if subtitles:
                logger.info(f"SRT file: {srt_output_file}")

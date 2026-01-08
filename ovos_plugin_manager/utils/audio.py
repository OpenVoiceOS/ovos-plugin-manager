"""
extracted from https://github.com/Uberi/speech_recognition

extended with methods to support conversion to/from numpy arrays
"""
import aifc
import audioop
import io
import os
import subprocess
import wave

try:
    import numpy as np

    Array = np.array  # Typing helper
except ImportError as e:
    np = None
    _np_exc = e
    from typing import Any

    Array = Any  # Typing helper


class AudioData:
    """
    Creates a new ``AudioData`` instance, which represents mono audio data.

    The raw audio data is specified by ``frame_data``, which is a sequence of bytes representing audio samples. This is the frame data structure used by the PCM WAV format.

    The width of each sample, in bytes, is specified by ``sample_width``. Each group of ``sample_width`` bytes represents a single audio sample.

    The audio data is assumed to have a sample rate of ``sample_rate`` samples per second (Hertz).
    """

    def __init__(self, frame_data, sample_rate: int, sample_width: int):
        assert sample_rate > 0, "Sample rate must be a positive integer"
        assert (
                sample_width % 1 == 0 and 1 <= sample_width <= 4
        ), "Sample width must be between 1 and 4 inclusive"
        self.frame_data = frame_data
        self.sample_rate = sample_rate
        self.sample_width = int(sample_width)

    @classmethod
    def from_file(cls, file_path: str) -> 'AudioData':
        """Creates a new ``AudioData`` instance from an audio file."""
        with AudioFile(file_path) as source:
            return source.read()

    @classmethod
    def from_array(cls, data: Array, sample_rate: int, sample_width: int) -> 'AudioData':
        if np is None:
            raise _np_exc

        if data.ndim != 1:
            raise ValueError("Input array must be mono (1-D)")

        # Normalize/scale to target integer range
        if np.issubdtype(data.dtype, np.floating):
            # Expected float range: -1.0 to +1.0
            max_val = float(2 ** (8 * sample_width - 1) - 1)
            scaled = np.clip(data, -1.0, 1.0) * max_val
            int_data = scaled.astype({
                                         1: np.uint8,  # will convert signed→unsigned below
                                         2: np.int16,
                                         3: np.int32,  # temporary; trimmed below
                                         4: np.int32
                                     }[sample_width])
        else:
            # Integer input: must be scaled into correct range
            int_data = data.astype({
                                       1: np.uint8,
                                       2: np.int16,
                                       3: np.int32,
                                       4: np.int32
                                   }[sample_width])

        # Special handling for sample_width == 1 (unsigned)
        if sample_width == 1:
            # Input is treated as signed; convert to unsigned PCM
            if np.issubdtype(int_data.dtype, np.signedinteger):
                int_data = (int_data.astype(np.int16) + 128).astype(np.uint8)

            frame_data = int_data.tobytes()
            return cls(frame_data, sample_rate, sample_width)

        # 24-bit PCM (sample_width = 3): trim to 3 bytes little-endian
        if sample_width == 3:
            # Ensure little-endian 32-bit, then slice off the highest byte
            is_le = int_data.dtype.byteorder in ('<', '=')
            le = int_data.astype('<i4') if not is_le else int_data
            raw32 = le.tobytes()
            # strip MSB of each 4-byte sample → [0:3], [4:7]->[4:7-1], ...
            frame_data = b"".join(
                raw32[i:i + 3] for i in range(0, len(raw32), 4)
            )
            return cls(frame_data, sample_rate, sample_width)

        # 16-bit or 32-bit: direct little-endian bytes
        int_data_le = int_data.astype('<i{}'.format(sample_width))
        frame_data = int_data_le.tobytes()
        return cls(frame_data, sample_rate, sample_width)

    def get_segment(self, start_ms=None, end_ms=None) -> 'AudioData':
        """
        Returns a new ``AudioData`` instance, trimmed to a given time interval. In other words, an ``AudioData`` instance with the same audio data except starting at ``start_ms`` milliseconds in and ending ``end_ms`` milliseconds in.

        If not specified, ``start_ms`` defaults to the beginning of the audio, and ``end_ms`` defaults to the end.
        """
        assert (
                start_ms is None or start_ms >= 0
        ), "``start_ms`` must be a non-negative number"
        assert end_ms is None or end_ms >= (
            0 if start_ms is None else start_ms
        ), "``end_ms`` must be a non-negative number greater or equal to ``start_ms``"
        if start_ms is None:
            start_byte = 0
        else:
            start_byte = int(
                (start_ms * self.sample_rate * self.sample_width) // 1000
            )
        if end_ms is None:
            end_byte = len(self.frame_data)
        else:
            end_byte = int(
                (end_ms * self.sample_rate * self.sample_width) // 1000
            )
        return AudioData(
            self.frame_data[start_byte:end_byte],
            self.sample_rate,
            self.sample_width,
        )

    def get_raw_data(self, convert_rate=None, convert_width=None) -> bytes:
        """
        Returns a byte string representing the raw frame data for the audio represented by the ``AudioData`` instance.

        If ``convert_rate`` is specified and the audio sample rate is not ``convert_rate`` Hz, the resulting audio is resampled to match.

        If ``convert_width`` is specified and the audio samples are not ``convert_width`` bytes each, the resulting audio is converted to match.

        Writing these bytes directly to a file results in a valid `RAW/PCM audio file <https://en.wikipedia.org/wiki/Raw_audio_format>`__.
        """
        assert (
                convert_rate is None or convert_rate > 0
        ), "Sample rate to convert to must be a positive integer"
        assert convert_width is None or (
                convert_width % 1 == 0 and 1 <= convert_width <= 4
        ), "Sample width to convert to must be between 1 and 4 inclusive"

        raw_data = self.frame_data

        # make sure unsigned 8-bit audio (which uses unsigned samples) is handled like higher sample width audio (which uses signed samples)
        if self.sample_width == 1:
            raw_data = audioop.bias(
                raw_data, 1, -128
            )  # subtract 128 from every sample to make them act like signed samples

        # resample audio at the desired rate if specified
        if convert_rate is not None and self.sample_rate != convert_rate:
            raw_data, _ = audioop.ratecv(
                raw_data,
                self.sample_width,
                1,
                self.sample_rate,
                convert_rate,
                None,
            )

        # convert samples to desired sample width if specified
        if convert_width is not None and self.sample_width != convert_width:
            if (
                    convert_width == 3
            ):  # we're converting the audio into 24-bit (workaround for https://bugs.python.org/issue12866)
                raw_data = audioop.lin2lin(
                    raw_data, self.sample_width, 4
                )  # convert audio into 32-bit first, which is always supported
                try:
                    audioop.bias(
                        b"", 3, 0
                    )  # test whether 24-bit audio is supported (for example, ``audioop`` in Python 3.3 and below don't support sample width 3, while Python 3.4+ do)
                except (
                        audioop.error
                ):  # this version of audioop doesn't support 24-bit audio (probably Python 3.3 or less)
                    raw_data = b"".join(
                        raw_data[i + 1: i + 4]
                        for i in range(0, len(raw_data), 4)
                    )  # since we're in little endian, we discard the first byte from each 32-bit sample to get a 24-bit sample
                else:  # 24-bit audio fully supported, we don't need to shim anything
                    raw_data = audioop.lin2lin(
                        raw_data, self.sample_width, convert_width
                    )
            else:
                raw_data = audioop.lin2lin(
                    raw_data, self.sample_width, convert_width
                )

        # if the output is 8-bit audio with unsigned samples, convert the samples we've been treating as signed to unsigned again
        if convert_width == 1:
            raw_data = audioop.bias(
                raw_data, 1, 128
            )  # add 128 to every sample to make them act like unsigned samples again

        return raw_data

    def get_wav_data(self, convert_rate=None, convert_width=None) -> bytes:
        """
        Returns a byte string representing the contents of a WAV file containing the audio represented by the ``AudioData`` instance.

        If ``convert_width`` is specified and the audio samples are not ``convert_width`` bytes each, the resulting audio is converted to match.

        If ``convert_rate`` is specified and the audio sample rate is not ``convert_rate`` Hz, the resulting audio is resampled to match.

        Writing these bytes directly to a file results in a valid `WAV file <https://en.wikipedia.org/wiki/WAV>`__.
        """
        raw_data = self.get_raw_data(convert_rate, convert_width)
        sample_rate = (
            self.sample_rate if convert_rate is None else convert_rate
        )
        sample_width = (
            self.sample_width if convert_width is None else convert_width
        )

        # generate the WAV file contents
        with io.BytesIO() as wav_file:
            wav_writer = wave.open(wav_file, "wb")
            try:  # note that we can't use context manager, since that was only added in Python 3.4
                wav_writer.setframerate(sample_rate)
                wav_writer.setsampwidth(sample_width)
                wav_writer.setnchannels(1)
                wav_writer.writeframes(raw_data)
                wav_data = wav_file.getvalue()
            finally:  # make sure resources are cleaned up
                wav_writer.close()
        return wav_data

    def get_aiff_data(self, convert_rate=None, convert_width=None) -> bytes:
        """
        Returns a byte string representing the contents of an AIFF-C file containing the audio represented by the ``AudioData`` instance.

        If ``convert_width`` is specified and the audio samples are not ``convert_width`` bytes each, the resulting audio is converted to match.

        If ``convert_rate`` is specified and the audio sample rate is not ``convert_rate`` Hz, the resulting audio is resampled to match.

        Writing these bytes directly to a file results in a valid `AIFF-C file <https://en.wikipedia.org/wiki/Audio_Interchange_File_Format>`__.
        """
        raw_data = self.get_raw_data(convert_rate, convert_width)
        sample_rate = (
            self.sample_rate if convert_rate is None else convert_rate
        )
        sample_width = (
            self.sample_width if convert_width is None else convert_width
        )

        # the AIFF format is big-endian, so we need to convert the little-endian raw data to big-endian
        if hasattr(
                audioop, "byteswap"
        ):  # ``audioop.byteswap`` was only added in Python 3.4
            raw_data = audioop.byteswap(raw_data, sample_width)
        else:  # manually reverse the bytes of each sample, which is slower but works well enough as a fallback
            raw_data = raw_data[sample_width - 1:: -1] + b"".join(
                raw_data[i + sample_width: i: -1]
                for i in range(sample_width - 1, len(raw_data), sample_width)
            )

        # generate the AIFF-C file contents
        with io.BytesIO() as aiff_file:
            aiff_writer = aifc.open(aiff_file, "wb")
            try:  # note that we can't use context manager, since that was only added in Python 3.4
                aiff_writer.setframerate(sample_rate)
                aiff_writer.setsampwidth(sample_width)
                aiff_writer.setnchannels(1)
                aiff_writer.writeframes(raw_data)
                aiff_data = aiff_file.getvalue()
            finally:  # make sure resources are cleaned up
                aiff_writer.close()
        return aiff_data

    def get_flac_data(self, convert_rate=None, convert_width=None) -> bytes:
        """
        Returns a byte string representing the contents of a FLAC file containing the audio represented by the ``AudioData`` instance.

        Note that 32-bit FLAC is not supported. If the audio data is 32-bit and ``convert_width`` is not specified, then the resulting FLAC will be a 24-bit FLAC.

        If ``convert_rate`` is specified and the audio sample rate is not ``convert_rate`` Hz, the resulting audio is resampled to match.

        If ``convert_width`` is specified and the audio samples are not ``convert_width`` bytes each, the resulting audio is converted to match.

        Writing these bytes directly to a file results in a valid `FLAC file <https://en.wikipedia.org/wiki/FLAC>`__.
        """
        assert convert_width is None or (
                convert_width % 1 == 0 and 1 <= convert_width <= 3
        ), "Sample width to convert to must be between 1 and 3 inclusive"

        if (
                self.sample_width > 3 and convert_width is None
        ):  # resulting WAV data would be 32-bit, which is not convertable to FLAC using our encoder
            convert_width = 3  # the largest supported sample width is 24-bit, so we'll limit the sample width to that

        # run the FLAC converter with the WAV data to get the FLAC data
        wav_data = self.get_wav_data(convert_rate, convert_width)
        flac_converter = get_flac_converter()
        if (
                os.name == "nt"
        ):  # on Windows, specify that the process is to be started without showing a console window
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= (
                subprocess.STARTF_USESHOWWINDOW
            )  # specify that the wShowWindow field of `startup_info` contains a value
            startup_info.wShowWindow = (
                subprocess.SW_HIDE
            )  # specify that the console window should be hidden
        else:
            startup_info = None  # default startupinfo
        process = subprocess.Popen(
            [
                flac_converter,
                "--stdout",
                "--totally-silent",
                # put the resulting FLAC file in stdout, and make sure it's not mixed with any program output
                "--best",  # highest level of compression available
                "-",  # the input FLAC file contents will be given in stdin
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            startupinfo=startup_info,
        )
        flac_data, stderr = process.communicate(wav_data)
        return flac_data

    def get_np_int16(self, convert_rate=None, convert_width=None) -> Array:
        if np is None:
            raise _np_exc
        audio_data = self.get_raw_data(convert_rate, convert_width)
        return np.frombuffer(audio_data, dtype=np.int16)

    def get_np_float32(self, normalize=True, convert_rate=None, convert_width=None) -> Array:
        audio_as_np_int16 = self.get_np_int16(convert_rate, convert_width)
        audio_as_np_float32 = audio_as_np_int16.astype(np.float32)
        if normalize:
            # Normalise float32 array so that values are between -1.0 and +1.0
            max_int16 = 2 ** 15
            return audio_as_np_float32 / max_int16
        return audio_as_np_float32


class AudioFile:
    """
    Creates a new ``AudioFile`` instance given a WAV/AIFF/FLAC audio file ``filename_or_fileobject``. Subclass of ``AudioSource``.

    If ``filename_or_fileobject`` is a string, then it is interpreted as a path to an audio file on the filesystem. Otherwise, ``filename_or_fileobject`` should be a file-like object such as ``io.BytesIO`` or similar.

    Note that functions that read from the audio (such as ``recognizer_instance.record`` or ``recognizer_instance.listen``) will move ahead in the stream. For example, if you execute ``recognizer_instance.record(audiofile_instance, duration=10)`` twice, the first time it will return the first 10 seconds of audio, and the second time it will return the 10 seconds of audio right after that. This is always reset to the beginning when entering an ``AudioFile`` context.

    WAV files must be in PCM/LPCM format; WAVE_FORMAT_EXTENSIBLE and compressed WAV are not supported and may result in undefined behaviour.

    Both AIFF and AIFF-C (compressed AIFF) formats are supported.

    FLAC files must be in native FLAC format; OGG-FLAC is not supported and may result in undefined behaviour.
    """

    def __init__(self, filename_or_fileobject):
        assert isinstance(filename_or_fileobject, (type(""), type(u""))) or hasattr(filename_or_fileobject,
                                                                                    "read"), "Given audio file must be a filename string or a file-like object"
        self.filename_or_fileobject = filename_or_fileobject
        self.stream = None
        self.DURATION = None

        self.audio_reader = None
        self.little_endian = False
        self.SAMPLE_RATE = None
        self.CHUNK = None
        self.FRAME_COUNT = None

    def __enter__(self):
        assert self.stream is None, "This audio source is already inside a context manager"
        try:
            # attempt to read the file as WAV
            self.audio_reader = wave.open(self.filename_or_fileobject, "rb")
            self.little_endian = True  # RIFF WAV is a little-endian format (most ``audioop`` operations assume that the frames are stored in little-endian form)
        except (wave.Error, EOFError):
            try:
                # attempt to read the file as AIFF
                self.audio_reader = aifc.open(self.filename_or_fileobject, "rb")
                self.little_endian = False  # AIFF is a big-endian format
            except (aifc.Error, EOFError):
                # attempt to read the file as FLAC
                if hasattr(self.filename_or_fileobject, "read"):
                    flac_data = self.filename_or_fileobject.read()
                else:
                    with open(self.filename_or_fileobject, "rb") as f:
                        flac_data = f.read()

                # run the FLAC converter with the FLAC data to get the AIFF data
                flac_converter = get_flac_converter()
                if os.name == "nt":  # on Windows, specify that the process is to be started without showing a console window
                    startup_info = subprocess.STARTUPINFO()
                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # specify that the wShowWindow field of `startup_info` contains a value
                    startup_info.wShowWindow = subprocess.SW_HIDE  # specify that the console window should be hidden
                else:
                    startup_info = None  # default startupinfo
                process = subprocess.Popen([
                    flac_converter,
                    "--stdout", "--totally-silent",
                    # put the resulting AIFF file in stdout, and make sure it's not mixed with any program output
                    "--decode", "--force-aiff-format",  # decode the FLAC file into an AIFF file
                    "-",  # the input FLAC file contents will be given in stdin
                ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, startupinfo=startup_info)
                aiff_data, _ = process.communicate(flac_data)
                aiff_file = io.BytesIO(aiff_data)
                try:
                    self.audio_reader = aifc.open(aiff_file, "rb")
                except (aifc.Error, EOFError):
                    raise ValueError(
                        "Audio file could not be read as PCM WAV, AIFF/AIFF-C, or Native FLAC; check if file is corrupted or in another format")
                self.little_endian = False  # AIFF is a big-endian format
        assert 1 <= self.audio_reader.getnchannels() <= 2, "Audio must be mono or stereo"
        self.SAMPLE_WIDTH = self.audio_reader.getsampwidth()

        # 24-bit audio needs some special handling for old Python versions (workaround for https://bugs.python.org/issue12866)
        samples_24_bit_pretending_to_be_32_bit = False
        if self.SAMPLE_WIDTH == 3:  # 24-bit audio
            try:
                audioop.bias(b"", self.SAMPLE_WIDTH,
                             0)  # test whether this sample width is supported (for example, ``audioop`` in Python 3.3 and below don't support sample width 3, while Python 3.4+ do)
            except audioop.error:  # this version of audioop doesn't support 24-bit audio (probably Python 3.3 or less)
                samples_24_bit_pretending_to_be_32_bit = True  # while the ``AudioFile`` instance will outwardly appear to be 32-bit, it will actually internally be 24-bit
                self.SAMPLE_WIDTH = 4  # the ``AudioFile`` instance should present itself as a 32-bit stream now, since we'll be converting into 32-bit on the fly when reading

        self.SAMPLE_RATE = self.audio_reader.getframerate()
        self.CHUNK = 4096
        self.FRAME_COUNT = self.audio_reader.getnframes()
        self.DURATION = self.FRAME_COUNT / float(self.SAMPLE_RATE)
        self.stream = AudioFile.AudioFileStream(self.audio_reader, self.little_endian,
                                                samples_24_bit_pretending_to_be_32_bit)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self.filename_or_fileobject,
                       "read"):  # only close the file if it was opened by this class in the first place (if the file was originally given as a path)
            self.audio_reader.close()
        self.stream = None
        self.DURATION = None

    def read(self, duration=None, offset=None) -> AudioData:
        """
        Records up to ``duration`` seconds of audio from ``source`` (an ``AudioSource`` instance) starting at ``offset`` (or at the beginning if not specified) into an ``AudioData`` instance, which it returns.

        If ``duration`` is not specified, then it will record until there is no more audio input.
        """
        assert self.stream is not None, "Audio source must be entered before recording, see documentation for ``AudioSource``; are you using ``source`` outside of a ``with`` statement?"

        frames = io.BytesIO()
        seconds_per_buffer = (self.CHUNK + 0.0) / self.SAMPLE_RATE
        elapsed_time = 0
        offset_time = 0
        offset_reached = False
        while True:  # loop for the total number of chunks needed
            if offset and not offset_reached:
                offset_time += seconds_per_buffer
                if offset_time > offset:
                    offset_reached = True

            buffer = self.stream.read(self.CHUNK)
            if len(buffer) == 0: break

            if offset_reached or not offset:
                elapsed_time += seconds_per_buffer
                if duration and elapsed_time > duration: break

                frames.write(buffer)

        frame_data = frames.getvalue()
        frames.close()
        return AudioData(frame_data, self.SAMPLE_RATE, self.SAMPLE_WIDTH)

    class AudioFileStream:
        def __init__(self, audio_reader, little_endian, samples_24_bit_pretending_to_be_32_bit):
            self.audio_reader = audio_reader  # an audio file object (e.g., a `wave.Wave_read` instance)
            self.little_endian = little_endian  # whether the audio data is little-endian (when working with big-endian things, we'll have to convert it to little-endian before we process it)
            self.samples_24_bit_pretending_to_be_32_bit = samples_24_bit_pretending_to_be_32_bit  # this is true if the audio is 24-bit audio, but 24-bit audio isn't supported, so we have to pretend that this is 32-bit audio and convert it on the fly

        def read(self, size=-1):
            buffer = self.audio_reader.readframes(self.audio_reader.getnframes() if size == -1 else size)
            if not isinstance(buffer, bytes): buffer = b""  # workaround for https://bugs.python.org/issue24608

            sample_width = self.audio_reader.getsampwidth()
            if not self.little_endian:  # big endian format, convert to little endian on the fly
                if hasattr(audioop,
                           "byteswap"):  # ``audioop.byteswap`` was only added in Python 3.4 (incidentally, that also means that we don't need to worry about 24-bit audio being unsupported, since Python 3.4+ always has that functionality)
                    buffer = audioop.byteswap(buffer, sample_width)
                else:  # manually reverse the bytes of each sample, which is slower but works well enough as a fallback
                    buffer = buffer[sample_width - 1::-1] + b"".join(
                        buffer[i + sample_width:i:-1] for i in range(sample_width - 1, len(buffer), sample_width))

            # workaround for https://bugs.python.org/issue12866
            if self.samples_24_bit_pretending_to_be_32_bit:  # we need to convert samples from 24-bit to 32-bit before we can process them with ``audioop`` functions
                buffer = b"".join(b"\x00" + buffer[i:i + sample_width] for i in range(0, len(buffer),
                                                                                      sample_width))  # since we're in little endian, we prepend a zero byte to each 24-bit sample to get a 32-bit sample
                sample_width = 4  # make sure we thread the buffer as 32-bit audio now, after converting it from 24-bit audio
            if self.audio_reader.getnchannels() != 1:  # stereo audio
                buffer = audioop.tomono(buffer, sample_width, 1, 1)  # convert stereo audio data to mono
            return buffer


def get_flac_converter():
    """Returns the absolute path of a FLAC converter executable, or raises an OSError if none can be found."""
    flac_converter = shutil_which("flac")  # check for installed version first
    if flac_converter is None:  # flac utility is not installed
        raise OSError(
            "FLAC conversion utility not available - consider installing the FLAC command line application by running `apt-get install flac` or your operating system's equivalent"
        )
    return flac_converter


def shutil_which(pgm):
    """Python 2 compatibility: backport of ``shutil.which()`` from Python 3"""
    path = os.getenv("PATH")
    for p in path.split(os.path.pathsep):
        p = os.path.join(p, pgm)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p


# patch for type checks in plugins to pass
try:
    import speech_recognition
    speech_recognition.AudioData = AudioData
except:
    pass

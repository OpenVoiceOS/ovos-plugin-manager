"""
original unmodified src from https://github.com/Uberi/speech_recognition shipped under ovos_plugin_manager.thirdparty.sr

extended with methods to support conversion to/from numpy arrays
"""
import io

from ovos_plugin_manager.thirdparty.sr import srAudioData, srAudioFile, get_flac_converter

try:
    import numpy as np

    Array = np.array  # Typing helper
except ImportError as e:
    np = None
    _np_exc = e
    from typing import Any

    Array = Any  # Typing helper


class AudioData(srAudioData):
    """
    Creates a new ``AudioData`` instance, which represents mono audio data.

    The raw audio data is specified by ``frame_data``, which is a sequence of bytes representing audio samples. This is the frame data structure used by the PCM WAV format.

    The width of each sample, in bytes, is specified by ``sample_width``. Each group of ``sample_width`` bytes represents a single audio sample.

    The audio data is assumed to have a sample rate of ``sample_rate`` samples per second (Hertz).
    """

    @classmethod
    def from_file(cls, file_path: str) -> 'AudioData':
        """
        Create an AudioData instance from the audio file at the given path.

        Parameters:
            file_path (str): Filesystem path to a WAV/AIFF/FLAC audio file.

        Returns:
            audio_data (AudioData): AudioData containing the file's mono PCM frame data, sample rate, and sample width.
        """
        with AudioFile(file_path) as source:
            return source.read()

    def save(self, file_path: str, convert_rate=None, convert_width=None):
        """
        Write the audio data to a WAV file at the given path.

        Optionally convert the sample rate or sample width before writing.

        Parameters:
            file_path (str): Filesystem path to write the WAV file to.
            convert_rate (int | None): Target sample rate in Hz to convert to, or `None` to keep the current rate.
            convert_width (int | None): Target sample width in bytes (e.g., 1, 2, 3, 4), or `None` to keep the current width.
        """
        with open(file_path, "wb") as f:
            f.write(self.get_wav_data(convert_rate, convert_width))

    @classmethod
    def from_array(cls, data: Array, sample_rate: int, sample_width: int) -> 'AudioData':
        """
        Create an AudioData instance from a 1-D NumPy array by converting the array into PCM frame bytes.
        
        Parameters:
            data (Array): 1-D NumPy array containing mono audio samples. If dtype is floating, values are expected in the range -1.0 to 1.0 and will be scaled to the target integer range. If dtype is integer, values will be cast to the target integer type for the specified sample width.
            sample_rate (int): Sample rate in Hz for the resulting AudioData.
            sample_width (int): Sample width in bytes per sample (1, 2, 3, or 4). When 1, output uses unsigned 8-bit PCM. When 3, samples are packed as 24-bit little-endian (3 bytes per sample).
        
        Returns:
            AudioData: New AudioData containing the PCM frame bytes produced from the input array, with the given sample_rate and sample_width.
        
        Raises:
            ValueError: If `data` is not a 1-D array (mono).
            Exception: Re-raises the stored NumPy import error if NumPy is not available.
        """
        if np is None:
            raise _np_exc

        if data.ndim != 1:
            raise ValueError("Input array must be mono (1-D)")

        # Normalize/scale to target integer range
        if np.issubdtype(data.dtype, np.floating):
            # Expected float range: -1.0 to +1.0
            max_val = float(2 ** (8 * sample_width - 1) - 1)
            scaled = np.clip(data, -1.0, 1.0) * max_val
            if sample_width == 1:
                # For 8-bit: scale to signed int8 range, then convert to unsigned
                int_data = scaled.astype(np.int8)
            else:
                int_data = scaled.astype({
                                         1: np.uint8,  # will convert signed→unsigned below
                                         2: np.int16,
                                         3: np.int32,  # temporary; trimmed below
                                         4: np.int32
                                     }[sample_width])
        else:
            # Integer input: cast to signed type first
            if sample_width == 1:
                int_data = data.astype(np.int8)
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
            # Convert signed int8 to unsigned uint8 PCM
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

    def get_np_int16(self, convert_rate=None) -> Array:
        """
        Produce a NumPy int16 array containing the audio samples.
        
        Parameters:
            convert_rate (int, optional): Target sample rate in Hz to convert to before extraction.
        
        Returns:
            numpy.ndarray: 1-D NumPy array of dtype `int16` with the audio samples (mono).
        
        Raises:
            Exception: Re-raises the original NumPy ImportError if NumPy is not available.
        """
        if np is None:
            raise _np_exc
        audio_data = self.get_raw_data(convert_rate, convert_width=2)
        return np.frombuffer(audio_data, dtype=np.int16)

    def get_np_float32(self, normalize=True, convert_rate=None) -> Array:
        """
        Return the audio as a NumPy float32 array.
        
        Parameters:
            normalize (bool): If True, scale samples to the range -1.0 to +1.0 by dividing by 2**15.
            convert_rate (int | None): Optional target sample rate to convert the audio to before conversion.
        
        Returns:
            Array: A NumPy array of dtype `float32` containing the audio samples; values are in [-1.0, 1.0] when `normalize` is True.
        """
        audio_as_np_int16 = self.get_np_int16(convert_rate)
        audio_as_np_float32 = audio_as_np_int16.astype(np.float32)
        if normalize:
            # Normalise float32 array so that values are between -1.0 and +1.0
            max_int16 = 2 ** 15
            return audio_as_np_float32 / max_int16
        return audio_as_np_float32

    def get_segment(self, start_ms=None, end_ms=None) -> 'AudioData':
        """
        Return an AudioData instance trimmed to the specified millisecond interval.

        Parameters:
            start_ms (float | int | None): Start time in milliseconds (inclusive). If None, start at the beginning.
            end_ms (float | int | None): End time in milliseconds (exclusive). If None, end at the end of the audio.

        Returns:
            AudioData: A new AudioData containing the audio frames from [start_ms, end_ms).
        """
        data: srAudioData = super().get_segment(start_ms, end_ms)
        # convert to patched AudioData class
        return AudioData(
            data.frame_data,
            data.sample_rate,
            data.sample_width,
        )


class AudioFile(srAudioFile):
    """
    Creates a new ``AudioFile`` instance given a WAV/AIFF/FLAC audio file ``filename_or_fileobject``. Subclass of ``AudioSource``.

    If ``filename_or_fileobject`` is a string, then it is interpreted as a path to an audio file on the filesystem. Otherwise, ``filename_or_fileobject`` should be a file-like object such as ``io.BytesIO`` or similar.

    Note that functions that read from the audio (such as ``recognizer_instance.record`` or ``recognizer_instance.listen``) will move ahead in the stream. For example, if you execute ``recognizer_instance.record(audiofile_instance, duration=10)`` twice, the first time it will return the first 10 seconds of audio, and the second time it will return the 10 seconds of audio right after that. This is always reset to the beginning when entering an ``AudioFile`` context.

    WAV files must be in PCM/LPCM format; WAVE_FORMAT_EXTENSIBLE and compressed WAV are not supported and may result in undefined behaviour.

    Both AIFF and AIFF-C (compressed AIFF) formats are supported.

    FLAC files must be in native FLAC format; OGG-FLAC is not supported and may result in undefined behaviour.
    """

    def read(self, duration=None, offset=None) -> AudioData:
        """
        Read up to `duration` seconds from the opened audio stream, beginning at `offset` seconds, and return an AudioData containing the captured PCM frames.
        
        Parameters:
            duration (float | None): Maximum number of seconds to read. If None, read until end of stream.
            offset (float | None): Number of seconds to skip from the start before recording. If None, begin immediately.
        
        Returns:
            AudioData: An AudioData instance holding the recorded frame bytes at the stream's sample rate and sample width.
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


# patch for type checks in plugins to pass
# TODO - remove in next major version
try:
    import speech_recognition

    speech_recognition.AudioData = AudioData
    speech_recognition.AudioFile = AudioFile
except ImportError:
    pass
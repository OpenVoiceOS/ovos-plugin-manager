# write your first unittest!
import unittest
from ovos_plugin_manager.templates.tts import TTS
from ovos_utils.messagebus import FakeBus


class TestSSML(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        tts = TTS()  # dummy engine
       # bus = FakeBus()
       # tts.init(bus)
        self.tts = tts

    def test_ssml(self):
        sentence = "<speak>Prosody can be used to change the way words " \
                   "sound. The following words are " \
                   "<prosody volume='x-loud'> " \
                   "quite a bit louder than the rest of this passage. " \
                   "</prosody> Each morning when I wake up, " \
                   "<prosody rate='x-slow'>I speak quite slowly and " \
                   "deliberately until I have my coffee.</prosody> I can " \
                   "also change the pitch of my voice using prosody. " \
                   "Do you like <prosody pitch='+5%'> speech with a pitch " \
                   "that is higher, </prosody> or <prosody pitch='-10%'> " \
                   "is a lower pitch preferable?</prosody></speak>"
        sentence_no_ssml = "Prosody can be used to change the way " \
                           "words sound. The following words are quite " \
                           "a bit louder than the rest of this passage. " \
                           "Each morning when I wake up, I speak quite " \
                           "slowly and deliberately until I have my " \
                           "coffee. I can also change the pitch of my " \
                           "voice using prosody. Do you like speech " \
                           "with a pitch that is higher, or is " \
                           "a lower pitch preferable?"
        sentence_bad_ssml = "<foo_invalid>" + sentence + \
                            "</foo_invalid end=whatever>"
        sentence_extra_ssml = "<whispered>whisper tts<\\whispered>"

        tts = TTS()  # dummy engine
        # test valid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence), sentence)

        # test extra ssml
        tts.ssml_tags = ['whispered']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         sentence_extra_ssml)

        # test unsupported extra ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         "whisper tts")

        # test mixed valid / invalid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_bad_ssml), sentence)

        # test unsupported ssml
        tts.ssml_tags = []
        self.assertEqual(tts.validate_ssml(sentence), sentence_no_ssml)

        self.assertEqual(tts.validate_ssml(sentence_bad_ssml),
                         sentence_no_ssml)

        self.assertEqual(TTS.remove_ssml(sentence), sentence_no_ssml)

    def test_format_speak_tags_with_speech(self):
        valid_output = "<speak>Speak This.</speak>"
        no_tags = TTS.format_speak_tags("Speak This.")
        self.assertEqual(no_tags, valid_output)

        leading_only = TTS.format_speak_tags("<speak>Speak This.")
        self.assertEqual(leading_only, valid_output)

        leading_with_exclusion = TTS.format_speak_tags("Nope.<speak>Speak This.")
        self.assertEqual(leading_with_exclusion, valid_output)

        trailing_only = TTS.format_speak_tags("Speak This.</speak>")
        self.assertEqual(trailing_only, valid_output)

        trailing_with_exclusion = TTS.format_speak_tags("Speak This.</speak> But not this.")
        self.assertEqual(trailing_with_exclusion, valid_output)

        tagged = TTS.format_speak_tags("<speak>Speak This.</speak>")
        self.assertEqual(tagged, valid_output)

        tagged_with_exclusion = TTS.format_speak_tags("Don't<speak>Speak This.</speak>But Not this.")
        self.assertEqual(tagged_with_exclusion, valid_output)

    def test_format_speak_tags_empty(self):
        leading_closure = TTS.format_speak_tags("</speak>hello.")
        self.assertFalse(leading_closure)

        trailing_open = TTS.format_speak_tags("hello.<speak>")
        self.assertFalse(trailing_open)

    def test_format_speak_tags_with_speech_no_tags(self):
        valid_output = "Speak This."
        no_tags = TTS.format_speak_tags("Speak This.", False)
        self.assertEqual(no_tags, valid_output)

        leading_only = TTS.format_speak_tags("<speak>Speak This.", False)
        self.assertEqual(leading_only, valid_output)

        leading_with_exclusion = TTS.format_speak_tags("Nope.<speak>Speak This.", False)
        self.assertEqual(leading_with_exclusion, valid_output)

        trailing_only = TTS.format_speak_tags("Speak This.</speak>", False)
        self.assertEqual(trailing_only, valid_output)

        trailing_with_exclusion = TTS.format_speak_tags("Speak This.</speak> But not this.", False)
        self.assertEqual(trailing_with_exclusion, valid_output)

        tagged = TTS.format_speak_tags("<speak>Speak This.</speak>", False)
        self.assertEqual(tagged, valid_output)

        tagged_with_exclusion = TTS.format_speak_tags("Don't<speak>Speak This.</speak>But Not this.", False)
        self.assertEqual(tagged_with_exclusion, valid_output)


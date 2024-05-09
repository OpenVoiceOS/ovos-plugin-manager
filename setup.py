import os
from setuptools import setup

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def get_version():
    """ Find the version of the package"""
    version = None
    version_file = os.path.join(BASEDIR, 'ovos_plugin_manager', 'version.py')
    major, minor, build, alpha = (None, None, None, None)
    with open(version_file) as f:
        for line in f:
            if 'VERSION_MAJOR' in line:
                major = line.split('=')[1].strip()
            elif 'VERSION_MINOR' in line:
                minor = line.split('=')[1].strip()
            elif 'VERSION_BUILD' in line:
                build = line.split('=')[1].strip()
            elif 'VERSION_ALPHA' in line:
                alpha = line.split('=')[1].strip()

            if ((major and minor and build and alpha) or
                    '# END_VERSION_BLOCK' in line):
                break
    version = f"{major}.{minor}.{build}"
    if alpha and int(alpha) > 0:
        version += f"a{alpha}"
    return version


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


def required(requirements_file):
    """ Read requirements file and remove comments and empty lines. """
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        if 'MYCROFT_LOOSE_REQUIREMENTS' in os.environ:
            print('USING LOOSE REQUIREMENTS!')
            requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
        return [pkg for pkg in requirements
                if pkg.strip() and not pkg.startswith("#")]


SEG_PLUGIN_ENTRY_POINT = 'ovos-segmentation-plugin-quebrafrases=ovos_plugin_manager.templates.segmentation:Segmenter'
TOK_PLUGIN_ENTRY_POINT = 'ovos-tokenization-plugin-quebrafrases=ovos_plugin_manager.templates.tokenization:Tokenizer'
POSTAG_PLUGIN_ENTRY_POINT = 'ovos-postag-plugin-dummy=ovos_plugin_manager.templates.postag:PosTagger'
KW_PLUGIN_ENTRY_POINT = 'ovos-keyword-plugin-dummy=ovos_plugin_manager.templates.keywords:KeywordExtractor'
TTS_PLUGIN_ENTRY_POINT = 'ovos-tts-plugin-dummy=ovos_plugin_manager.templates.tts:TTS'
STT_PLUGIN_ENTRY_POINT = 'ovos-stt-plugin-dummy=ovos_plugin_manager.templates.stt:STT'
WW_PLUGIN_ENTRY_POINT = 'ovos-ww-plugin-dummy=ovos_plugin_manager.templates.hotwords:HotWordEngine'

with open(os.path.join(BASEDIR, "README.md"), "r") as f:
    long_description = f.read()

setup(
    name='ovos-plugin-manager',
    version=get_version(),
    packages=['ovos_plugin_manager',
              'ovos_plugin_manager.templates',
              'ovos_plugin_manager.utils',
              'ovos_plugin_manager.hardware',
              'ovos_plugin_manager.hardware.led'],
    url='https://github.com/OpenVoiceOS/OVOS-plugin-manager',
    license='Apache-2.0',
    author='jarbasAi',
    install_requires=required("requirements/requirements.txt"),
    package_data={'': package_files('ovos-plugin-manager')},
    author_email='jarbas@openvoiceos.com',
    description='OpenVoiceOS plugin manager',
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        'intentbox.segmentation': SEG_PLUGIN_ENTRY_POINT,
        'intentbox.tokenization': TOK_PLUGIN_ENTRY_POINT,
        'intentbox.postag': POSTAG_PLUGIN_ENTRY_POINT,
        'intentbox.keywords': KW_PLUGIN_ENTRY_POINT,
        'mycroft.plugin.tts': TTS_PLUGIN_ENTRY_POINT,
        'mycroft.plugin.stt': STT_PLUGIN_ENTRY_POINT,
        'mycroft.plugin.wake_word': WW_PLUGIN_ENTRY_POINT
    }
)

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


setup(
    name='ovos-plugin-manager',
    version=get_version(),
    packages=['ovos_plugin_manager',
              'ovos_plugin_manager.templates',
              'ovos_plugin_manager.utils'],
    url='https://github.com/OpenVoiceOS/OVOS-plugin-manager',
    license='Apache-2.0',
    author='jarbasAi',
    install_requires=["ovos_utils>=0.0.15",
                      "requests~=2.26",
                      "combo_lock~=0.2.1",
                      "memory-tempfile"],
    author_email='jarbasai@mailfence.com',
    description='OpenVoiceOS plugin manager'
)

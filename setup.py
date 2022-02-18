from setuptools import setup


def _get_version():
    with open('ovos_plugin_manager/versioning/opm_versions.py') as versions:
        for line in versions:
            if line.startswith('CURRENT_OPM_VERSION'):
                # CURRENT_OSM_VERSION = "0.0.10a9" --> "0.0.10a9"
                return line.replace('"','').strip('\n').split('= ')[1]


setup(
    name='ovos-plugin-manager',
    version=_get_version(),
    packages=['ovos_plugin_manager', 'ovos_plugin_manager.templates', 'ovos_plugin_manager.utils'],
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

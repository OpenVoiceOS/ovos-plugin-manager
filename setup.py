from setuptools import setup

setup(
    name='ovos-plugin-manager',
    version='0.0.3a4',
    packages=['ovos_plugin_manager', 'ovos_plugin_manager.templates', 'ovos_plugin_manager.utils'],
    url='https://github.com/OpenVoiceOS/OVOS-plugin-manager',
    license='Apache-2.0',
    author='jarbasAi',
    install_requires=["ovos_utils>=0.0.12a3",
                      "requests",
                      "memory-tempfile"],
    author_email='jarbasai@mailfence.com',
    description='OpenVoiceOS plugin manager'
)

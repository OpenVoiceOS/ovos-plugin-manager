import fileinput
from os.path import join, dirname

version_file = join(dirname(__file__), "ovos_plugin_manager", "versioning",
                    "opm_versions.py")
version_var_name = "CURRENT_OPM_VERSION"

with open(version_file, "r", encoding="utf-8") as v:
    for line in v.readlines():
        if line.startswith(version_var_name):
            if '"' in line:
                version = line.split('"')[1]
            else:
                version = line.split("'")[1]

if "a" not in version:
    parts = version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    version = '.'.join(parts)
    version = f"{version}a0"
else:
    post = version.split("a")[1]
    new_post = int(post) + 1
    version = version.replace(f"a{post}", f"a{new_post}")

for line in fileinput.input(version_file, inplace=True):
    if line.startswith(version_var_name):
        print(f"{version_var_name} = \"{version}\"")
    else:
        print(line.rstrip('\n'))

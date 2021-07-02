import glob
import subprocess

for file in glob.glob("examples/**/*.json", recursive=True):
    if not "3D" in file:
        continue

    print(file)
    command = ["python", "polyfem_to_ipc_script.py", "-i", file]
    subprocess.run(command)
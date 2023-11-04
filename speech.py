from subprocess import call, Popen

def speak(text_to_speak, speed=270, asynchronous=True):
    if asynchronous:
        Popen(["espeak", f"-s{speed} -ven+18 -z", text_to_speak])
    else:
        call(["espeak", f"-s{speed} -ven+18 -z", text_to_speak])

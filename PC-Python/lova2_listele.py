import frida
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
for p in dev.enumerate_processes():
    if "lova" in p.name.lower() or p.pid == 3553:
        print(p.pid, p.name)
print("---")
# Genis arama
for p in dev.enumerate_processes():
    print(p.pid, p.name)

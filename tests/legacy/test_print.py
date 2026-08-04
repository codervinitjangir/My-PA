import sys
with open('print_test.log', 'w') as f:
    f.write(f"sys.stdout is {type(sys.stdout)}\n")
    try:
        print("test print")
        f.write("print succeeded\n")
    except Exception as e:
        f.write(f"print failed: {e}\n")

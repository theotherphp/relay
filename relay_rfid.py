import mercury

reader = mercury.Reader('tmr:///dev/ttyUSB0')
reader.set_region('NA2')
reader.set_read_plan([1], 'GEN2')
reader.write('0000')
for epc_obj in reader.read():
	epc = repr(epc_obj).strip('\'')  # ugh
	hex_numbers = [epc[i:i+2] for i in range(0, len(epc), 2)]
	chars = [chr(int(ch, 16)) for ch in hex_numbers]
	print ''.join(chars)

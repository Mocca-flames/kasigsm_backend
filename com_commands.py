import serial
ser = serial.Serial('COM5', 115200, timeout=2)
ser.write(b'AT+DEVCONINFO\r\n')
print(ser.read(1000).decode())
ser.close()
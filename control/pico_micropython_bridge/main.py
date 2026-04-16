import sys
import time

try:
    import uselect as select
except ImportError:
    import select

from machine import Pin, PWM


PIN_MOTOR_PWM_RIGHT1 = 7
PIN_MOTOR_PWM_RIGHT2 = 6
PIN_MOTOR_PWM_RIGHT3 = 9
PIN_MOTOR_PWM_RIGHT4 = 8
PIN_MOTOR_PWM_LEFT1 = 18
PIN_MOTOR_PWM_LEFT2 = 19
PIN_MOTOR_PWM_LEFT3 = 21
PIN_MOTOR_PWM_LEFT4 = 20

MOTOR_SPEED_MIN = -100
MOTOR_SPEED_MAX = 100
DEFAULT_SPEED = 50
PWM_FREQ = 500
FAILSAFE_MS = 750


def make_pwm(pin_number):
    pwm = PWM(Pin(pin_number))
    pwm.freq(PWM_FREQ)
    pwm.duty_u16(0)
    return pwm


LEFT1_FORWARD = make_pwm(PIN_MOTOR_PWM_LEFT1)
LEFT1_REVERSE = make_pwm(PIN_MOTOR_PWM_LEFT2)
LEFT2_FORWARD = make_pwm(PIN_MOTOR_PWM_LEFT3)
LEFT2_REVERSE = make_pwm(PIN_MOTOR_PWM_LEFT4)
RIGHT1_FORWARD = make_pwm(PIN_MOTOR_PWM_RIGHT1)
RIGHT1_REVERSE = make_pwm(PIN_MOTOR_PWM_RIGHT2)
RIGHT2_FORWARD = make_pwm(PIN_MOTOR_PWM_RIGHT3)
RIGHT2_REVERSE = make_pwm(PIN_MOTOR_PWM_RIGHT4)

motors_running = False
last_command_at = time.ticks_ms()
run_until = None


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def parse_int(parts, index, fallback):
    try:
        return int(parts[index])
    except (IndexError, ValueError):
        return fallback


def speed_to_duty(speed):
    return int(abs(speed) * 65535 / MOTOR_SPEED_MAX)


def write_motor(forward_pwm, reverse_pwm, speed):
    speed = clamp(speed, MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
    duty = speed_to_duty(speed)
    if speed >= 0:
        forward_pwm.duty_u16(duty)
        reverse_pwm.duty_u16(0)
    else:
        forward_pwm.duty_u16(0)
        reverse_pwm.duty_u16(duty)


def set_wheels(m1_speed, m2_speed, m3_speed, m4_speed):
    write_motor(LEFT1_FORWARD, LEFT1_REVERSE, m1_speed)
    write_motor(LEFT2_FORWARD, LEFT2_REVERSE, m2_speed)
    write_motor(RIGHT1_FORWARD, RIGHT1_REVERSE, m3_speed)
    write_motor(RIGHT2_FORWARD, RIGHT2_REVERSE, m4_speed)


def set_differential(left_speed, right_speed):
    set_wheels(left_speed, left_speed, right_speed, right_speed)


def stop_motors():
    global motors_running, run_until
    set_wheels(0, 0, 0, 0)
    motors_running = False
    run_until = None


def arm_stop(duration_ms):
    global last_command_at, motors_running, run_until
    now = time.ticks_ms()
    last_command_at = now
    motors_running = True
    if duration_ms > 0:
        run_until = time.ticks_add(now, duration_ms)
    else:
        run_until = None


def normalise_line(line):
    return line.strip().upper().replace("#", " ").replace(",", " ")


def handle_command(line):
    global last_command_at

    command_line = normalise_line(line)
    if not command_line:
        return

    parts = command_line.split()
    command = parts[0]

    if command == "PING":
        print("PONG")
        return

    if command in ("S", "STOP"):
        last_command_at = time.ticks_ms()
        stop_motors()
        print("OK STOP")
        return

    if command == "DRIVE":
        left_speed = clamp(parse_int(parts, 1, DEFAULT_SPEED), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        right_speed = clamp(parse_int(parts, 2, DEFAULT_SPEED), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        duration_ms = clamp(parse_int(parts, 3, 0), 0, 5000)
        set_differential(left_speed, right_speed)
        arm_stop(duration_ms)
        print("OK DRIVE")
        return

    if command in ("WHEEL", "WHEELS"):
        m1_speed = clamp(parse_int(parts, 1, 0), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        m2_speed = clamp(parse_int(parts, 2, 0), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        m3_speed = clamp(parse_int(parts, 3, 0), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        m4_speed = clamp(parse_int(parts, 4, 0), MOTOR_SPEED_MIN, MOTOR_SPEED_MAX)
        duration_ms = clamp(parse_int(parts, 5, 0), 0, 5000)
        set_wheels(m1_speed, m2_speed, m3_speed, m4_speed)
        arm_stop(duration_ms)
        print("OK WHEEL")
        return

    speed = clamp(abs(parse_int(parts, 1, DEFAULT_SPEED)), 0, MOTOR_SPEED_MAX)
    duration_ms = clamp(parse_int(parts, 2, 0), 0, 5000)

    if command in ("F", "FORWARD", "W"):
        set_differential(speed, speed)
    elif command in ("B", "BACK", "BACKWARD"):
        set_differential(-speed, -speed)
    elif command in ("L", "LEFT"):
        set_differential(-speed, speed)
    elif command in ("R", "RIGHT"):
        set_differential(speed, -speed)
    elif command in ("ML", "MOVE_LEFT", "STRAFE_LEFT"):
        set_wheels(-speed, speed, -speed, speed)
    elif command in ("MR", "MOVE_RIGHT", "STRAFE_RIGHT"):
        set_wheels(speed, -speed, speed, -speed)
    else:
        print("ERR UNKNOWN {}".format(command))
        return

    arm_stop(duration_ms)
    print("OK MOVE")


def enforce_failsafe():
    if not motors_running:
        return
    now = time.ticks_ms()
    if run_until is not None and time.ticks_diff(now, run_until) >= 0:
        stop_motors()
        print("OK AUTO_STOP")
        return
    if time.ticks_diff(now, last_command_at) > FAILSAFE_MS:
        stop_motors()
        print("OK FAILSAFE_STOP")


def main():
    stop_motors()
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    print("READY micropython_serial_bridge")

    while True:
        events = poller.poll(10)
        if events:
            line = sys.stdin.readline()
            if line:
                handle_command(line)
        enforce_failsafe()


main()

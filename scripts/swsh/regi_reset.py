from __future__ import annotations

import argparse
import contextlib
import sys
import time
from collections.abc import Generator

import cv2
import numpy
import serial

SERIAL_DEFAULT = 'COM1' if sys.platform == 'win32' else '/dev/ttyUSB0'


def _press(ser: serial.Serial, s: str, duration: float = .1) -> None:
    print(f'{s=} {duration=}')
    ser.write(s.encode())
    time.sleep(duration)
    ser.write(b'0')
    time.sleep(.075)


def _getframe(vid: cv2.VideoCapture) -> numpy.ndarray:
    _, frame = vid.read()
    cv2.imshow('game', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        raise SystemExit(0)
    return frame


def _wait_and_render(vid: cv2.VideoCapture, t: float) -> None:
    end = time.time() + t
    while time.time() < end:
        _getframe(vid)


def _alarm(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
    while True:
        ser.write(b'!')
        _wait_and_render(vid, .5)
        ser.write(b'.')
        _wait_and_render(vid, .5)


def _await_pixel(
        ser: serial.Serial,
        vid: cv2.VideoCapture,
        *,
        x: int,
        y: int,
        pixel: tuple[int, int, int],
        timeout: float = 90,
) -> None:
    end = time.time() + timeout
    frame = _getframe(vid)
    while not numpy.array_equal(frame[y][x], pixel):
        frame = _getframe(vid)
        if time.time() > end:
            _alarm(ser, vid)


def _await_not_pixel(
        ser: serial.Serial,
        vid: cv2.VideoCapture,
        *,
        x: int,
        y: int,
        pixel: tuple[int, int, int],
        timeout: float = 90,
) -> None:
    end = time.time() + timeout
    frame = _getframe(vid)
    while numpy.array_equal(frame[y][x], pixel):
        frame = _getframe(vid)
        if time.time() > end:
            _alarm(ser, vid)


@contextlib.contextmanager
def _shh(ser: serial.Serial) -> Generator[None, None, None]:
    try:
        yield
    finally:
        ser.write(b'.')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    args = parser.parse_args()

    vid = cv2.VideoCapture(0)
    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    with serial.Serial(args.serial, 9600) as ser, _shh(ser):
        while True:
            _press(ser, 'H')
            _wait_and_render(vid, 1)
            _press(ser, 'X')
            _wait_and_render(vid, 1)
            _press(ser, 'A')
            # TODO: we could notice the dialog quicker here
            _wait_and_render(vid, 3.5)
            _press(ser, 'A')
            _wait_and_render(vid, 1)
            _press(ser, 'A')

            _await_pixel(ser, vid, x=5, y=5, pixel=(16, 16, 16))

            print('startup screen!')

            _await_not_pixel(ser, vid, x=5, y=5, pixel=(16, 16, 16))

            print('after startup!')
            _wait_and_render(vid, .75)
            _press(ser, 'A')

            _await_pixel(ser, vid, x=5, y=5, pixel=(16, 16, 16))
            _await_not_pixel(ser, vid, x=5, y=5, pixel=(16, 16, 16))

            print('game loaded')
            _wait_and_render(vid, .75)
            _press(ser, 'A')
            _wait_and_render(vid, .5)
            _press(ser, 'A')
            _wait_and_render(vid, .75)
            _press(ser, 'A')

            _await_pixel(ser, vid, x=696, y=420, pixel=(59, 59, 59))

            print('dialog started')

            _await_not_pixel(ser, vid, x=696, y=420, pixel=(59, 59, 59))

            print('dialog ended')
            t0 = time.time()

            _await_pixel(ser, vid, x=696, y=420, pixel=(59, 59, 59))

            t1 = time.time()
            print(f'dialog delay: {t1 - t0:.3f}s')

            if (t1 - t0) > 1:
                print('SHINY!!!')
                _alarm(ser, vid)

    vid.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

rpi-player-buttons
==================

This is a part of [rpi-player](https://github.com/drudv/rpi-player) that controls Mopidy's playback and volume using 3 buttons connected to Raspberry Pi GPIO connectors

## Instalation

Requirements: Python 3

```bash
git clone https://github.com/drudv/rpi-player
cd rpi-player-buttons/
pip install .
```

## Usage

```bash
rpi-player-buttons --gpio-pause 22 --gpio-volume-up 17 --gpio-volume-down 27
```

## License

[MIT](../LICENSE)

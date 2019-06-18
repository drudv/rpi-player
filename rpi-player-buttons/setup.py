from setuptools import setup
setup(
    name='rpi_player_buttons',
    version='0.1.0',
    packages=['rpi_player_buttons'],
    install_requires=['RPi.GPIO', 'websocket', 'websocket-client'],
    python_requires='>3.5',
    entry_points={
        'console_scripts': [
            'rpi-player-buttons = rpi_player_buttons.main:main'
        ]
    })

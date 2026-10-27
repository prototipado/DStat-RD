from setuptools import find_packages, setup


setup(
    name="dstat-gui-dev2",
    version="2.1.0",
    description="DStat potentiostat GUI, Python 3 / Qt6 edition",
    license="GPL-3.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PyQt6>=6.4",
        "matplotlib>=3.7",
        "numpy>=1.24",
        "packaging>=23.0",
        "pandas>=2.0",
        "pyserial>=3.5",
        "pyzmq>=25.0",
        "scipy>=1.10",
        "seaborn>=0.12",
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": ["dstat-gui=dstat_interface.main:main"],
    },
)

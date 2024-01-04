"""Update universe.pkl for static universe loading."""

from json import load
from pickle import dump
from time import time

from util import DataGenerator

with open("config.json") as f:
    CONFIG = load(f)

start = time()
data_gen = DataGenerator(CONFIG["tokens"]["github"], branch="christmas")
data_gen.reload_all()

with open("universe.pkl", "wb") as f:
    dump(data_gen.universe, f)

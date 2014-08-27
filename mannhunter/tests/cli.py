"""Tiny applications for testing Mannhunter"""

import time

import click


@click.group()
def main():
    pass


@main.command()
def memory_leak():
    """Slowly consumes memory"""
    data = list()
    while True:
        data.extend(range(5000))
        time.sleep(0.1)

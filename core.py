# -*- coding: utf-8 -*-
# vim: set ts=4 et

import select
import time

import config
from connection import RemoteServer
import hooks
from message import Message
import plugin


def tick():
    global selectables
    global time_last

    time_now = time.time()
    if time_last + 1 <= time_now:
        time_last = time_now
        for obj in selectables:
            obj.on_tick(time_now)
        hooks.call_event('tick', time_now)

    try_read = []
    try_write = []

    for obj in selectables:
        if obj.fileno() == None:
            continue
        if obj.can_read():
            try_read.append(obj)
        if obj.can_write():
            try_write.append(obj)

    readable, writeable, _ = select.select(try_read, try_write, [], 0.5)

    for obj in writeable:
        obj.do_write()
    for obj in readable:
        obj.do_read()


def run():
    global client
    global selectables
    global connected, running, in_shutdown
    global time_last

    client = RemoteServer(config.host, config.ssl)
    client.process_line = lambda line: hooks.call_event('line', client, line)

    for name in config.autoload_plugins:
        plugin.load(name, client)

    client.connect()

    selectables = [client]
    time_last = time.time()

    in_shutdown = False
    running = True
    connected = False
    while running:
        try:
            tick()
        except KeyboardInterrupt:
            shutdown('KeyboardInterrupt')
        if client.connected and not connected:
            hooks.call_event('connect')
            connected = True
        if not client.connected and connected:
            hooks.call_event('disconnect')
            connected = False
        if in_shutdown and not connected:
            running = False

    for name in plugin.plugins.keys():
        plugin.unload(name, True)


def shutdown(reason=''):
    global client
    global running, in_shutdown

    if client.connected:
        client.send('QUIT :%s' % reason)
        client.do_write()

    if in_shutdown:
        running = False

    in_shutdown = True


#!/home/dragonfly/miniforge3/envs/active_optics/bin/python
# -*- coding: utf-8 -*- 

import datetime
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import NestedCompleter

from dragonfly import state as state
from dragonfly import commands as commands

device_colors = {
    "aluma": "<cyan>",
    "starchaser": "<violet>",
    "lens": "<orange>",
    "powerbox": "<blue>",
    "filter_tilter": "<green>"
}

def get_toolbar():
    state.load_state("master")
    devices = ["starchaser","aluma", "filter_tilter", "lens", "powerbox"]
    now = datetime.datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")
    device_string = ""
    for device in devices:
        if state.current_master_state[device]["busy"] is True:
            device_string = device_string + device + " (" + state.current_master_state[device]["current_action"] + ") "
                            
    return HTML("<b><style bg='red'>{}</style></b> {}".format(
            time_string,
            device_string))

def print_line(subsystem, subsystem_line):
    color = device_colors[subsystem]
    slash_color = color.replace("<","</")
    if state.current_master_state[subsystem]["selected"]:
        print_formatted_text(HTML('<u><i>' + color + subsystem_line + 
        slash_color + '</i></u>'))
    else:
        print_formatted_text(HTML(color + subsystem_line + slash_color))

def print_summary():
    "Provide a colorful summary of the current state of a Dragonfly element."
    lens_string = "{:<15}  position: {}  stabilizing: {}".format(
        "[LENS]",
        state.current_master_state["lens"]["position"],
        state.current_master_state["lens"]["stabilizing"]
    )
    
    starchaser_string = ("{:<15}  exptime: {}  binning: {}"
                         "  exposing: {}  repeat: {}  keep: {}  guiding: {}") .format(
        "[STARCHASER]",
        state.current_master_state["starchaser"]["exptime"],
        state.current_master_state["starchaser"]["binning"],
        state.current_master_state["starchaser"]["exposing"],
        state.current_master_state["starchaser"]["repeat"],
        state.current_master_state["starchaser"]["keep"],
        state.current_master_state["starchaser"]["guiding"]
    )

    aluma_string = ("{:<15}  exptime: {}  binning: {}"
                   "  exposing: {}  repeat: {}  keep: {}  setpoint: {}  temperature: {}  power: {}").format(
        "[ALUMA]",
        state.current_master_state["aluma"]["exptime"],
        state.current_master_state["aluma"]["binning"],
        state.current_master_state["aluma"]["exposing"],
        state.current_master_state["aluma"]["repeat"],
        state.current_master_state["aluma"]["keep"],
        state.current_master_state["aluma"]["setpoint"],
        state.current_master_state["aluma"]["temperature"],
        state.current_master_state["aluma"]["power"]
     )

    filter_tilter_string = "{:<15}  angle: {}".format(
        "[FILTER_TILTER]",
        state.current_master_state["filter_tilter"]["angle"]
    )

    powerbox_string = "{:<15}  P1: {}  current: {}  temperature: {}  humidity: {}".format(
        "[POWERBOX]",
        state.current_master_state["powerbox"]["P1"],
        state.current_master_state["powerbox"]["current"],
        state.current_master_state["powerbox"]["temperature"],
        state.current_master_state["powerbox"]["humidity"]
    )

    print("")
    print_line("starchaser", starchaser_string)
    print_line("aluma", aluma_string)
    print_line("filter_tilter", filter_tilter_string)
    print_line("lens", lens_string)
    print_line("powerbox", powerbox_string)
    print("")


# Key interface elements

df_completer = NestedCompleter.from_nested_dict(commands.command_dict)

style = Style.from_dict({
        'completion-menu.completion': 'bg:#008888 #ffffff',
        'completion-menu.completion.current': 'bg:#00aaaa #000000',
        'scrollbar.background': 'bg:#88aaaa',
        'scrollbar.button': 'bg:#222222',
    })



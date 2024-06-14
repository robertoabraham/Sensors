from dragonfly import state as state
from dragonfly import utility as utility
from schema import Schema, And, Or, Use, Optional, SchemaError, Regex

# Adding a command is a two-step process.
#
# 1. Add tests in check_command() to validate the new command.
#
# 2. Add the new command to the  commands variable so the prompting system
#    incorportes the command into the command-completion system.

class DragonflyCommandError(Exception):
    "Command does not match definition."
    pass

def check_command(command_string):
    """
    Parses a string into a canonical command dictionary (wth 'verb' 'noun' 'argument' keys) and 
    validates the command to make sure it's something the Dragonfly array will understand. 
    """

    try:
        # split the string into a list of 3 elements, which we will
        # test individually.
        command_list = command_string.split()
        if len(command_list) >= 3:
            command_list[0] = command_list[0].lower()
            command_list[1] = command_list[1].lower()
            command_list[2] = command_list[2].lower()
        if len(command_list) == 2:
            command_list[0] = command_list[0].lower()
            command_list[1] = command_list[1].lower()
            command_list.append(None) 
        elif len(command_list) == 1:
            command_list[0] = command_list[0].lower()
            command_list.append(None) 
            command_list.append(None) 
        [verb,noun,arg] = command_list
        noun = utility.convert_to_number_or_bool_or_None(noun)
        arg = utility.convert_to_number_or_bool_or_None(arg) 

        # Verbs
        verb_test = Regex(r'^analyze$|^expose$|^focus$|^guide$|^help$|^load$|^quit$|^save$|^select$|^set$|^tilt$|^update$')

        # Nouns (note that 'expose', 'focus', and 'help' currently take no arguments.
        noun_test = {}
        noun_test['analyze'] = Regex(r'^fwhm$|^statistics$|^background$')
        noun_test['guide'] = Regex(r'^start$|^stop')
        noun_test['load'] = Schema(str)
        noun_test['select'] = Regex(r'^aluma$|^starchaser$|^filter_tilter$|^lens$|^powerbox$')
        noun_test['set'] = Regex(r'^binning$|^count$|^exptime$|^keep$|^repeat$|^setpoint$|^target$|^position$|^focusmode$|^focustrack$|^verbose$|^displaymode$|^displayrange$')
        noun_test['tilt'] = Schema(Or(int,float)) 
        noun_test['update'] = Regex(r'^aluma$|^starchaser$|^filter_tilter$|^lens$|^powerbox$|^all$')

        # Arguments
        arg_test = {}
        arg_test['binning'] = Schema(int)
        arg_test['count'] = Schema(int)
        arg_test['exptime'] = Schema(Or(int,float))
        arg_test['setpoint'] = Schema(Or(int,float))
        arg_test['repeat'] = Schema(bool)
        arg_test['keep'] = Schema(bool)
        arg_test['target'] = Schema(str)
        arg_test['position'] = Schema(int)
        arg_test['focusmode'] = Regex(r'^fft$|^lost$|^coarse$|^fine$')
        arg_test['focustrack'] = Schema(bool)
        arg_test['select'] = Regex(r'^filter_tilter|^lens|^aluma|^starchaser')
        arg_test['update'] = Regex(r'^filter_tilter|^lens|^aluma|^starchaser')
        arg_test['verbose'] = Schema(bool)
        arg_test['displaymode'] = Regex(r'^full$|^corners$|^sky$')  
        arg_test['displayrange'] = Schema(And([Or(int,float),Or(int,float)],list)) 
        arg_test['displayunit'] = Regex(r'^adu$|^sigma$')  
        arg_test['displaytrans'] = Regex(r'^sqrt$|^linear$')

        command = {}
        command['verb'] = verb_test.validate(verb)

        if (noun is not None) and (verb in noun_test.keys()):
            command['noun'] = noun_test[verb].validate(noun)
        else:
            command['noun'] = None

        if (arg is not None) and (noun in arg_test.keys()):
            command['arg'] = arg_test[noun].validate(arg)
        else:
            command['arg'] = None
    except:
        raise DragonflyCommandError

    return command

# Actions

def select(command_dict):
    state.load_state("master")
    state.current_master_state["lens"]["selected"] = False
    state.current_master_state["filter_tilter"]["selected"] = False
    state.current_master_state["powerbox"]["selected"] = False
    state.current_master_state["aluma"]["selected"] = False
    state.current_master_state["starchaser"]["selected"] = False
    noun = command_dict["noun"]
    state.current_master_state[noun]["selected"] = True
    state.save_state("master")
   
# Interface sugar.
 
# These are all commands known to the script. This is only used to provide
# command completion to the prompting system.

command_dict = {
    "analzye": {
        "fwhm": None,
        "statistics": None,
        "background": None
    }, 
    "expose": None,
    "focus": None,
    "guide": {
            "on": None,
            "off": None
    },
    "help": None, 
    "load":
        {"<string>": None},
    "quit": None,
    "save":
        {"<string>": None},  
    "select": {
            "aluma": None,
            "starchaser": None,
            "filter_tilter": None,
            "powerbox": None,
    },
    "set": {
        "binning": {
            "<int>": None
        },
        "count": {
            "<int>": None
        },
        "exptime": {
            "<float>": None
        },
        "camera": {
            "aluma": None,
            "starchaser": None
        },
        "keep": {
            "<bool>": None,
        },
        "position": {
            "<int>": None
        },
        "repeat": {
            "<bool>": None,
        },
        "target": {
            "<string>": None
        },
       "focusmode": {
            "fft": None,
            "lost": None,
            "coarse": None,
            "fine": None
        },
        "focustrack": {
            "on": None,
            "off": None
        },
        "verbose": {
            "on": None,
            "off": None
        },
        "displaymode": {
            "full": None,
            "zoom": None,
            "hybrid": None
        },
        "displayrange": {
           "<[low,high]>": None
        },
        "displayunit": {
            "adu": None,
            "sigma": None
        }, 
        "displaytrans": {
            "sqrt": None,
            "linear": None
        }          
    },
    "tilt": {
        "<float>": None
    },
    "update": {
        "all": None,
        "aluma": None,
        "starchaser": None,
        "filter_tilter": None,
        "powerbox": None
    }
 }


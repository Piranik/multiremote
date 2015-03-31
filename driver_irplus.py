"""
Improved IR driver which uses a separate config file to produce
desired results.

JSON config file looks like this:

{
  "commandfile" : "<file with IR commands>",
  "commandlist" : {
    "<command>..." : {
      "type" : <see commandtype.py>,
      "name" : "<readable name>", (optional)
      "description" : "<readable description>" (optional)
      "sequence" : "[<ircmd>|<ms>]..." (optional)
    }
  }
}

If you omit the optional items, they get the command name as name/desc/sequence.
Any sequence item which is all numbers is considered to be a delay of X milliseconds.

For example:

{
  "file" : "projector.json",
  "commands" : {
    "on" : {
      "type" : 901,
    },
    "off" : {
      "type" : 902,
      "sequence" : "off,200,off"
    }
  }
}

NOTE!
For automatic power management to work, you need to define an on and an off
sequence. If you miss either or both, the power manegement will not happen.

"""

from driver_null import DriverNull
import requests
import base64
import json
from commandtype import CommandType

class DriverIRPlus(DriverNull):
  def __init__(self, server, commandfile):
    DriverNull.__init__(self)

    self.server = server
    self.cmd_on = None
    self.cmd_off = None

    jdata = open(commandfile)
    data = json.load(jdata)

    jdata = open(data["file"])
    self.ircmds = json.load(jdata)

    for cmd in data["commands"]:
      self.COMMAND_HANDLER[cmd] = {
        "arguments"   : 0, 
        "handler"     : self.sendCommand, 
        "extras"      : cmd,
        "name"        : cmd,
        "description" : cmd,
        "type"        : data["commands"][cmd]["type"]
      }
      if "sequence" in data["commands"][cmd]:
        self.COMMAND_HANDLER[cmd]["extras"] = data["commands"][cmd]["sequence"]
      if "name" in data["commands"][cmd]:
        self.COMMAND_HANDLER[cmd]["name"] = data["commands"][cmd]["name"]
      if "description" in data["commands"][cmd]:
        self.COMMAND_HANDLER[cmd]["description"] =  data["commands"][cmd]["description"]
      if data["commands"][cmd]["type"] == 901:
        self.cmd_on = cmd
      if data["commands"][cmd]["type"] == 902:
        self.cmd_off = cmd

  def setPower(self, enable):
    """
    We need to override this and use the on/off pair or toggle to handle
    power.
    """
    if self.power == enable:
      return True

    if enable and self.cmd_on is not None:
      self.sendCommand(None, self.COMMAND_HANDLER[self.cmd_on]["extras"])
    elif self.cmd_off is not None:
      self.sendCommand(None, self.COMMAND_HANDLER[self.cmd_off]["extras"])

    self.power = enable
    return True

  def sendCommand(self, zone, command):
    seq = command.split(",")
    for cmd in seq:
      if cmd.isdigit():
        time.sleep(int(cmd))
      else:
        self.sendIr(cmd)

  def sendIr(self, command):
    if not command in self.ircmds:
      print "WARN: %s is not a defined IR command" % command

    ir = self.ircmds[command]

    url = self.server + "/write/" + ir
    r = requests.get(url)
    if r.status_code != 200:
      print "ERROR: Driver was unable to execute %s" % url
      return False

    j = r.json()
# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import os
import sys


import octoprint.plugin
from octoprint.events import Events
import RPi.GPIO as GPIO
from time import sleep
from flask import jsonify

class GpioshutdownPlugin(
						octoprint.plugin.StartupPlugin,
						octoprint.plugin.ShutdownPlugin,
						octoprint.plugin.EventHandlerPlugin,
						octoprint.plugin.TemplatePlugin,
						octoprint.plugin.SettingsPlugin
						):

	##~~ SettingsPlugin mixin

	def initialize(self):
		self.activated = 0
		self._logger.info("Running RPi.GPIO version '{0}'".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":       # Need at least 0.6 for edge detection
			raise Exception("RPi.GPIO must be greater than 0.6")
		GPIO.setwarnings(False)        # Disable GPIO warnings

	def on_after_startup(self):
		self._logger.info("GPIOShutdown Plugin Starting...")
		self._setup_sensor()

	def on_shutdown(self):
		self._shutdown_sensor()

	@property
	def pin_shutdown(self):
		return int(self._settings.get(["pin_shutdown"]))

	@property
	def pin_led(self):
		return int(self._settings.get(["pin_led"]))

	@property
	def bounce(self):
		return int(self._settings.get(["bounce"]))

	def get_template_configs(self):
		return [dict(type="settings", custom_bindings=False)]

	def _setup_sensor(self):
		try:
			GPIO.cleanup()
		except:
			self._logger.exception("Error cleanup the GPIO")

		if self.shutdown_pin_enabled() or self.led_pin_enabled():
			GPIO.setmode(GPIO.BCM)

		if self.shutdown_pin_enabled():
			GPIO.setup(self.pin_shutdown, GPIO.IN, pull_up_down=GPIO.PUD_UP)
			GPIO.add_event_detect(
						self.pin_shutdown, GPIO.BOTH,
						callback=self.sensor_callback,
						bouncetime=self.bounce
						)

		if self.led_pin_enabled():
			GPIO.setup(self.pin_led, GPIO.OUT, initial=GPIO.HIGH)
			GPIO.output(self.pin_led, GPIO.HIGH)


	def _shutdown_sensor(self):
		if self.led_pin_enabled():
			try:
				GPIO.output(self.pin_led, GPIO.LOW)
			except:
				self._logger.exception("Unable to turn off the ready-to-run led.")
						

	def sensor_callback(self, _):
		sleep(self.bounce/1000)
		if self.activated==1:
			return

		self.activated = 1
		self._logger.info("Sensor triggered!")
		try:
			os.system("sudo shutdown -h now")
		except:
			e = sys.exc_info()[0]
			self._logger.exception("Error executing shutdown command")




	def get_settings_defaults(self):
		return dict(
			pin_shutdown	= -1,   # Default is no pin
			pin_led			= -1,   # Default is no pin
			bounce			= 250,  # Debounce 250ms
		)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		self._setup_sensor()

	def shutdown_pin_enabled(self):
		return self.pin_shutdown != -1

	def led_pin_enabled(self):
		return self.pin_led != -1



	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/GPIOShutdown.js"],
			css=["css/GPIOShutdown.css"],
			less=["less/GPIOShutdown.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			GPIOShutdown=dict(
				displayName="GPIO Shutdown",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="fmalekpour",
				repo="OctoPrint-Gpioshutdown",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/fmalekpour/OctoPrint-Gpioshutdown/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "GPIO Shutdown"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = GpioshutdownPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}


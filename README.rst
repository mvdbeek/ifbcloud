ifbcloud commandline utility
----------------------------

This is a commandline utility to 

  - quickly get the status of instances launched
  - start new instances
  - stop instances

Installation
------------

``pip install ifbcloud``

Useage:
-------

To get the current status, do

``ifbcoud status -u <your_ifb_username> -p <your_ifb_password>``

To lauch a new instance, do

``ifbcloud start -u <your_ifb_username> -p <your_ifb_password> -n <name_for_your_instance>``

To see your currently defined disks, do

``ifbcloud disks -u <your_ifb_username> -p <your_ifb_password>``

To launch an instance and attach the disk named ``disk0``, do

``ifbcloud start -u <your_ifb_username> -p <your_ifb_password> -n <name_for_your_instance> -dn disk0``

To stop an instance, do

``ifbcloud stop -u <your_ifb_username> -p <your_ifb_password> -n <name_for_your_instance>``

More options are available in the subcommands help section.

Shortcuts
---------
If you don't want to repetitively type your username and password (and have it stored in your shell's history),
you can export the environmental variables ``IFB_USERNAME`` and ``IFB_PASSWORD`` and omit the ``-u`` and ``-p`` options.

Limitations
-----------
We're currently just launching the Docker appliance (number 206), which is what I'm using all the time.
PR's to improve this are welcome. You can extract the instance id's from the dashboard's html.

Similarly, you can attach permanent storage to your new instances, but you first need to manually create the disks
in the `IFB cloud storage interface <https://cloud.france-bioinformatique.fr/cloud/storage/>`_.

This utility is not using any public API, just reverse-engineered from the browser's post requests, so this may
start failing at any time if the IFB upgrades their cloud service.

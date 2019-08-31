# Simple defining several timers for controlling devices during day
For instance controlling of filtration in swimming pool, well pump

Tested on *hass.io* ver. 0.93.2 and higher

This published version is more stable and close done to required standard of HA development rules.

Example of using turnoffon:

![Turnoffon](https://github.com/JiriKursky/Custom_components/blob/master/library/example_pump.JPG)



Example of turn_on/turn_off of filtration in intervals:
10:20 - 20 minutes
17:00 - 20:50

In these intervals will each minute calling service *turn_on* - *input_boolean.filtration". Outside then *turn_off*. 

Add to your *configuration.yaml*
```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "10:20":20, "17:00":"20:50" }      
```

Component automatically create *turnoffon.filtration* - main (parent for controlling) and *turnoffon.filtration_01* , *turnoffon.filtration_02* (children). "Automation is automatically" in component

You can stop calling turn_on/turn_off with condition explained below or with state = 'off' of parent entity.

Each child has these attributes:

![Attributes](https://github.com/JiriKursky/Custom_components/blob/master/library/turnoffon_attr.JPG)

That's all!
<a href="https://bmc.xyz/l/turnoffon" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/white_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

___
*Timing*

You can add there days of weeks:

```yaml
timers: { "6:50":"7:00", "12:00":5 }    
weekdays: ['mon', 'tue', 'thu']
```
Only in this weekdays will be switch on

all possible values of weekdays:

```yaml
WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
```
___
*Component input_datetime*

![Climate](https://github.com/JiriKursky/Custom_components/blob/master/library/AC_example.JPG)

If you need run-time change time intervals, you can use input_datetime component:

```yaml
climate:  
  input_datetime: true
  force_turn: false  
  action_entity_id: input_boolean.klima_chlazeni
  linked_entity_id: switch.klima_chlazeni
  name: A/C timer
  timers: { "6:50":"7:00", "12:00":5 }    
```

Automatically will be created components start end time.

___
# Example of more complex solution with several parents and their children
*configuration.yaml*:

```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      condition_run: input_boolean.filtration_timer
    pump:
      action_entity_id: input_boolean.pump
      timers: { "6:05":15, "07:00":15, "08:05":15, "08:45":15, "09:30":15, "10:15":15, "14:00":15, "16:05":15, "18:00":15, "19:00":15, "20:15":15, "21:05":15, "22:15":15, "22:55":15 }      
      condition_run: input_boolean.pump_timer
    sprinkler_1:
      action_entity_id: input_boolean.sprinkler_1
      name: Area 1
      timers: { "12:00":"16:00","21:00":"22:00" }      
    sprinkler_2:
      action_entity_id: input_boolean.sprinkler_2
      name: Area 2
      timers: { "8:00":"10:00","16:00":"18:00" }      
    sprinkler_3:
      action_entity_id: input_boolean.sprinkler_3
      name: Area 3
      timers: { "6:00":"8:00","18:00":"20:00" }      
    sprinkler_4:
      action_entity_id: input_boolean.sprinkler_4
      name: Area 4
      timers: { "10:00":"12:00","22:00":"23:59" }
```
Explanation
```yaml
turnoffon:    
    # Entity domain - do not change
    #
    filtration:
    # Entity_id. Will be created turnoffon.filtration
    #
      action_entity_id: input_boolean.filtration
      # Will be called with turn_on in defined interval and with turn_off outside this interval      
      #
      timers: { "6:10":50, "10:10":30, "12:00":30, "13:10":2, "15:00":20, "17:00":20, "18:00":50, "20:00":30, "21:20":5 }      
      # Definition turn_on intervals 
      # "6:10":50 start at 6:10 for 50 minutes - do not exceed 59 minutes! do not put commas etc. 
      # warning do not use "24:00"
      # ----------------
      # Second possibilty of define timer "6:10":"8:00" 
      condition_run: input_boolean.filtration_timer
      # App is testing this for 'on' or 'off'. You will stop automatisation. I am using for instance for sprinkler in rainy days      
```
Next feature
you can add force_turn: false (default is true). It will lead that HA will not repeating turn_on/turn_off each minute. It is useful if you are using for instance device with "beep" during setting on/off. HA is reading current state of entity it means if it shoulf be off and is on it is sending command turn_off. This you should have in your mind if you want manually control device also. In that case I advice to add input_boolean as action_entity_id and linked

example of force run:

```yaml
turnoffon:
    climate:
      action_entity_id: switch.climate_cooling
      name: Climate living room
      timers: { "12:00":"16:00","21:00":"22:00" }      
      force_run: false 
```    

# Full example of climate controlling

```yaml
- platform: broadlink
  host: 192.168.X.X
  mac: "ma:c0:ad:dr:es:s0"
  type: rm2_pro_plus
  switches:      
    climate_cooling:
      friendly_name: My climate control
      command_on: 'JgBOAAABKZYUExQ3FRIVNRUTFBMVExQTFTYXNRQ3FBBMWEhURFhIVEhcRFREXNBURFxEVERcRFhEXERY1FBIXNBQSFxAXNRYSFAANBQAAAAAAAAAAAAA='
      command_off: 'JgBOAAABKJcUExU2FRIUFBMTFRMUExUTFTYUNxQ2FRIVExUTFRMUExQUExMUNxQSFBQTExYSFRIWEhQ3FBIVNhMTFRIVNxUTFAANBQAAAAAAAAAAAAA='

input_boolean:
    climate_control:
        name: Ctl climate
    climate_sensor:
        name: Temp to control
turnoffon:
    climate:
      action_entity_id: input_boolean.climate_control
      linked_entity_id: switch.climate_cooling
      name: Climate living room
      timers: { "8:00":"11:00","21:00":"22:00" }      
      force_run: false 
      condition_run: input_boolean.climate_sensor
```
What will happened:

if input_boolean.climate_sensor will be off, nothing happened and all off/on will not work
if input_boolean.climate_sensor is on or you will not put condition_run it will:

in time intervals 8:00-11:00 and 21:00-22:00 will turn_on input_boolean.climate_control, but only once if input_boolean.climate_control
if input_boolean.climate_control will turn_on, also linked entity switch.climate_cooling will go turn_on and the same in off.

*Why is there linked_entity_id and it is not simply put to action_entity_id like this?*
```yaml
turnoffon:
    climate:
      action_entity_id: switch.climate_cooling      
      name: Climate living room
      timers: { "8:00":"11:00","21:00":"22:00" }      
      force_run: false 
      condition_run: input_boolean.climate_sensor
```
It will work. However if you want manually switch on between 11:00-21:00 it will during one minute go off. In case of previous solution you can control it and you are able manually switch off in 11:00-21:00.
___
# Services
*turnoffon.set_time*

![Service](https://github.com/JiriKursky/Custom_components/blob/master/library/turnoffon_service_delta.JPG)

*Why there is climate_02?*

during setup is turnoffon create for each timer its children. Parent is turnoffon.climate. It is creating climate_01 for 8-11 and climate_02 for 21-22.

Calling this service will change interval from 21-22 to 19:15-19:16.
There is in example force_run = false. It means that after restart will it stay in 19:15-19:16. In case force_run = true it will ignore or your changes via service.



# FAQ
*Why is there force_run: false?*

If it is missing or force_run: true, each minute it will send turn_on or turn_off to device. In this case if you have action_entity_id: switch.climate_cooling it can beep each minute or doing reset etc. 

*I've changed timers but there are old values*

You must use service turnoffon.reset_timers

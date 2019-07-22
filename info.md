# Turnoffon

# Simple defining several timers for controlling devices during day
For instance controlling of filtration in swimming pool, well pump, air condition

![Turnoffon](https://github.com/JiriKursky/Custom_components/blob/master/library/example_pump.JPG)

{% if not installed %}
## Installation

1. Click install.
2. Add platform `turnoffon:` to your HA configuration.

```yaml
turnoffon:
    filtration:
      action_entity_id: input_boolean.filtration
      timers: { "10:20":20, "17:00":"20:50" }      
```
{% endif %}

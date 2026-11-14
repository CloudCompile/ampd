import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = ["@tonearm"]

tidbyt_a2dp_ns = cg.global_ns.namespace("tidbyt_a2dp")
TidbytA2DPSource = tidbyt_a2dp_ns.class_("TidbytA2DPSource", cg.Component)

CONF_DEVICE_NAME = "device_name"
CONF_URL = "url"

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(TidbytA2DPSource),
    cv.Required(CONF_DEVICE_NAME): cv.string,
    cv.Required(CONF_URL): cv.string,
}).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID], config[CONF_DEVICE_NAME],
                           config[CONF_URL])
    await cg.register_component(var, config)

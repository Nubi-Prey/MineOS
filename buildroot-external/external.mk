# buildroot-external/external.mk
include $(sort $(wildcard $(BR2_EXTERNAL_MINEOS_PATH)/package/*/*.mk))

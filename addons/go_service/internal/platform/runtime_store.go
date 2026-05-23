package platform

func ReadRuntimeProfile() map[string]any {
	return map[string]any{"profile": "local-deterministic", "ready": true}
}

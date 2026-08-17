export const config = {
  serviceName: 'node-ops-service',
  port: Number(process.env.PORT || 8080),
  runtimeProfile: process.env.RUNTIME_PROFILE || 'local-deterministic',
  secretKey: process.env.SECRET_KEY || '',
};

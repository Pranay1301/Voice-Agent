const BIAS = 0x84;
const CLIP = 32635;

/**
 * Converts a 16-bit linear PCM sample to 8-bit μ-law byte
 * @param {number} sample 
 * @returns {number}
 */
function linearToMulaw(sample) {
  const sign = (sample >> 8) & 0x80;
  if (sign !== 0) sample = -sample;
  if (sample > CLIP) sample = CLIP;
  sample += BIAS;
  let exponent = 7;
  for (let expMask = 0x4000; (sample & expMask) === 0 && exponent > 0; exponent--, expMask >>= 1) {}
  const mantissa = (sample >> (exponent + 3)) & 0x0F;
  const mulaw = ~(sign | (exponent << 4) | mantissa);
  return mulaw & 0xFF;
}

/**
 * Converts an 8-bit μ-law byte to 16-bit linear PCM sample
 * @param {number} mulawByte 
 * @returns {number}
 */
function mulawToLinear(mulawByte) {
  const mulaw = ~mulawByte;
  const sign = mulaw & 0x80;
  const exponent = (mulaw & 0x70) >> 4;
  const data = mulaw & 0x0F;
  let sample = data << 3;
  sample += 0x84;
  sample <<= exponent;
  sample -= BIAS;
  return sign === 0 ? sample : -sample;
}

/**
 * Converts a 16-bit PCM Buffer to 8-bit μ-law Buffer
 * @param {Buffer} pcmBuffer 
 * @returns {Buffer}
 */
function pcmBufferToMulaw(pcmBuffer) {
  const numSamples = pcmBuffer.length / 2;
  const out = Buffer.alloc(numSamples);
  for (let i = 0; i < numSamples; i++) {
    const sample = pcmBuffer.readInt16LE(i * 2);
    out[i] = linearToMulaw(sample);
  }
  return out;
}

/**
 * Converts an 8-bit μ-law Buffer to 16-bit PCM Buffer
 * @param {Buffer} mulawBuffer 
 * @returns {Buffer}
 */
function mulawBufferToPcm(mulawBuffer) {
  const out = Buffer.alloc(mulawBuffer.length * 2);
  for (let i = 0; i < mulawBuffer.length; i++) {
    const sample = mulawToLinear(mulawBuffer[i]);
    out.writeInt16LE(sample, i * 2);
  }
  return out;
}

/**
 * Simple linear interpolation resampler
 * @param {Buffer} inputBuffer (16-bit PCM)
 * @param {number} fromRate 
 * @param {number} toRate 
 * @returns {Buffer}
 */
function resample(inputBuffer, fromRate, toRate) {
  if (fromRate === toRate) return inputBuffer;
  const ratio = fromRate / toRate;
  const outLength = Math.floor(inputBuffer.length / 2 / ratio);
  const outBuffer = Buffer.alloc(outLength * 2);
  for (let i = 0; i < outLength; i++) {
    const inIdx = Math.floor(i * ratio);
    const val = inputBuffer.readInt16LE(inIdx * 2);
    outBuffer.writeInt16LE(val, i * 2);
  }
  return outBuffer;
}

/**
 * Helper: 16kHz PCM → 8kHz μ-law (e.g. ElevenLabs to Twilio)
 * @param {Buffer} pcmBuffer 
 * @returns {Buffer}
 */
function pcm16kToMulaw8k(pcmBuffer) {
  const resampled = resample(pcmBuffer, 16000, 8000);
  return pcmBufferToMulaw(resampled);
}

module.exports = {
  linearToMulaw,
  mulawToLinear,
  pcmBufferToMulaw,
  mulawBufferToPcm,
  resample,
  pcm16kToMulaw8k
};

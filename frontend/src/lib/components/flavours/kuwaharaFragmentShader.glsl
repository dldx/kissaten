#define SECTOR_COUNT 8

uniform int radius;
uniform sampler2D inputBuffer;
uniform vec4 resolution;
uniform sampler2D originalTexture;

varying vec2 vUv;

float random(vec2 c) {
  return fract(sin(dot(c.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

vec4 fromLinear(vec4 linearRGB) {
    bvec3 cutoff = lessThan(linearRGB.rgb, vec3(0.0031308));
    vec3 higher = vec3(1.055)*pow(linearRGB.rgb, vec3(1.0/2.4)) - vec3(0.055);
    vec3 lower = linearRGB.rgb * vec3(12.92);

    return vec4(mix(higher, lower, cutoff), linearRGB.a);
}

vec3 sampleColor(vec2 offset) {
    vec2 coord = (gl_FragCoord.xy + offset) / resolution.xy;
    return texture2D(originalTexture, coord).rgb;
}

vec4 getDominantOrientation(vec4 structureTensor) {
    float Jxx = structureTensor.r;
    float Jyy = structureTensor.g;
    float Jxy = structureTensor.b;

    float trace = Jxx + Jyy;
    float determinant = Jxx * Jyy - Jxy * Jxy;

    float lambda1 = trace * 0.5 + sqrt(trace * trace * 0.25 - determinant);
    float lambda2 = trace * 0.5 - sqrt(trace * trace * 0.25 - determinant);

    float jxyStrength = abs(Jxy) / (abs(Jxx) + abs(Jyy) + abs(Jxy) + 1e-6);

    vec2 v;

    if (jxyStrength > 0.0) {
        v = normalize(vec2(-Jxy, Jxx - lambda1));
    } else {
        v = vec2(0.0, 1.0);
    }

    return vec4(normalize(v), lambda1, lambda2);
}

float polynomialWeight(float x, float y, float eta, float lambda) {
    float polyValue = (x + eta) - lambda * (y * y);
    return max(0.0, polyValue * polyValue);
}

void getSectorVarianceAndAverageColor(mat2 anisotropyMat, float angle, float radius, out vec3 avgColor, out float variance) {
    vec3 weightedColorSum = vec3(0.0);
    vec3 weightedSquaredColorSum = vec3(0.0);
    float totalWeight = 0.0;

    float eta = 0.1;
    float lambda = 0.5;

    for (float r = 1.0; r <= radius; r += 1.0) {
        for (float a = -0.392699; a <= 0.392699; a += 0.196349) {
            vec2 sampleOffset = r * vec2(cos(angle + a), sin(angle + a));
            sampleOffset *= anisotropyMat;

            vec3 color = sampleColor(sampleOffset);
            float weight = polynomialWeight(sampleOffset.x, sampleOffset.y, eta, lambda);

            weightedColorSum += color * weight;
            weightedSquaredColorSum += color * color * weight;
            totalWeight += weight;
        }
    }

    // Calculate average color and variance
    avgColor = weightedColorSum / totalWeight;
    vec3 varianceRes = (weightedSquaredColorSum / totalWeight) - (avgColor * avgColor);
    variance = dot(varianceRes, vec3(0.299, 0.587, 0.114)); // Convert to luminance
}

void main() {
    vec4 structureTensor = texture2D(inputBuffer, vUv);

    vec3 sectorAvgColors[SECTOR_COUNT];
    float sectorVariances[SECTOR_COUNT];

    vec4 orientationAndAnisotropy = getDominantOrientation(structureTensor);
    vec2 orientation = orientationAndAnisotropy.xy;

    float anisotropy = (orientationAndAnisotropy.z - orientationAndAnisotropy.w) / (orientationAndAnisotropy.z + orientationAndAnisotropy.w + 1e-6);

    float alpha = 25.0;
    float scaleX = alpha / (anisotropy + alpha);
    float scaleY = (anisotropy + alpha) / alpha;

    mat2 anisotropyMat = mat2(orientation.x, -orientation.y, orientation.y, orientation.x) * mat2(scaleX, 0.0, 0.0, scaleY);

    for (int i = 0; i < SECTOR_COUNT; i++) {
      float angle = float(i) * 6.28318 / float(SECTOR_COUNT); // 2π / SECTOR_COUNT
      getSectorVarianceAndAverageColor(anisotropyMat, angle, float(radius), sectorAvgColors[i], sectorVariances[i]);
    }

    float minVariance = sectorVariances[0];
    vec3 finalColor = sectorAvgColors[0];

    for (int i = 1; i < SECTOR_COUNT; i++) {
        if (sectorVariances[i] < minVariance) {
            minVariance = sectorVariances[i];
            finalColor = sectorAvgColors[i];
        }
    }

    vec4 color = vec4(finalColor, 1.0);
    gl_FragColor = fromLinear(color);
}
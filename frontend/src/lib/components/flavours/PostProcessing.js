import { Pass } from "postprocessing";
import * as THREE from "three";
import tensorFragmentShader from "./tensorFragmentShader.glsl?raw";
import kuwaharaFragmentShader from "./kuwaharaFragmentShader.glsl?raw";
import finalFragmentShader from "./finalFragmentShader.glsl?raw";

const tensorShader = {
  uniforms: {
    inputBuffer: { value: null },
    resolution: {
      value: new THREE.Vector4(),
    },
  },
  vertexShader: `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);


    // Set the final position of the vertex
    gl_Position = projectionMatrix * modelViewPosition;
  }
  `,
  fragmentShader: tensorFragmentShader,
};

class TensorPass extends Pass {
  constructor(args) {
    super();

    this.material = new THREE.ShaderMaterial(tensorShader);
    this.fullscreenMaterial = this.material;
    this.resolution = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );
  }

  dispose() {
    this.material.dispose();
  }

  render(renderer, writeBuffer, readBuffer) {
    this.material.uniforms.inputBuffer.value = readBuffer.texture;
    this.material.uniforms.resolution.value = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );

    if (this.renderToScreen) {
      renderer.setRenderTarget(null);
      renderer.render(this.scene, this.camera);
    } else {
      renderer.setRenderTarget(writeBuffer);
      if (this.clear) renderer.clear();
      renderer.render(this.scene, this.camera);
    }
  }
}

const kuwaharaShader = {
  uniforms: {
    inputBuffer: { value: null },
    resolution: {
      value: new THREE.Vector4(),
    },
    originalTexture: { value: null },
    radius: { value: 10.0 },
  },
  vertexShader: `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);


    // Set the final position of the vertex
    gl_Position = projectionMatrix * modelViewPosition;
  }
  `,
  fragmentShader: kuwaharaFragmentShader,
};

class KuwaharaPass extends Pass {
  constructor(args) {
    super();

    this.material = new THREE.ShaderMaterial(kuwaharaShader);
    this.fullscreenMaterial = this.material;
    this.resolution = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );
    this.radius = args.radius;
    this.originalSceneTarget = args.originalSceneTarget;
  }

  dispose() {
    this.material.dispose();
  }

  render(renderer, writeBuffer, readBuffer) {
    this.material.uniforms.resolution.value = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );
    this.material.uniforms.radius.value = this.radius;
    this.material.uniforms.inputBuffer.value = readBuffer.texture;
    this.material.uniforms.originalTexture.value = this.originalSceneTarget.texture;

    if (this.renderToScreen) {
      renderer.setRenderTarget(null);
      renderer.render(this.scene, this.camera);
    } else {
      renderer.setRenderTarget(writeBuffer);
      if (this.clear) renderer.clear();
      renderer.render(this.scene, this.camera);
    }
  }
}

const finalShader = {
  uniforms: {
    inputBuffer: { value: null },
    resolution: {
      value: new THREE.Vector4(),
    },
    watercolorTexture: { value: null },
  },
  vertexShader: `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);


    // Set the final position of the vertex
    gl_Position = projectionMatrix * modelViewPosition;
  }
  `,
  fragmentShader: finalFragmentShader,
};

class FinalPass extends Pass {
  constructor(args) {
    super();

    this.material = new THREE.ShaderMaterial(finalShader);
    this.fullscreenMaterial = this.material;
    this.material.uniforms.resolution.value = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );
    this.resolution = new THREE.Vector4(
      window.innerWidth * Math.min(window.devicePixelRatio, 2),
      window.innerHeight * Math.min(window.devicePixelRatio, 2),
      1 / (window.innerWidth * Math.min(window.devicePixelRatio, 2)),
      1 / (window.innerHeight * Math.min(window.devicePixelRatio, 2))
    );

    // Add the watercolor texture to the uniforms
    this.material.uniforms.watercolorTexture = {
      value: args.watercolorTexture,
    };
  }

  dispose() {
    this.material.dispose();
  }

  render(renderer, writeBuffer, readBuffer) {
    this.material.uniforms.inputBuffer.value = readBuffer.texture;

    if (this.renderToScreen) {
      renderer.setRenderTarget(null);
      renderer.render(this.scene, this.camera);
    } else {
      renderer.setRenderTarget(writeBuffer);
      if (this.clear) renderer.clear();
      renderer.render(this.scene, this.camera);
    }
  }
}

export { TensorPass, KuwaharaPass, FinalPass };


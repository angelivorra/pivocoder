# Referencia de Plugins de Audio instalados en el sistema

Este archivo documenta los plugins LV2, LADSPA, VST2 y VST3 disponibles en el sistema para su uso como referencia al solicitar cadenas de efectos, procesamiento de audio o instrumentos.

---

## Template de referencia: `prod/template03.carxp`

Template base validado y funcional para el micrófono. Define la cadena de limpieza de entrada de audio y la entrada MIDI del controlador.

### Cadena de señal

```
system:capture_1 (micro, mono)
  ├─► Carla:audio-in1
  └─► Carla:audio-in2
         │
         ▼
   [Calf Filter]  ← paso alto 12dB/oct a 100 Hz, elimina rumble/bajas
         │
         ▼
   [Calf Gate]    ← noise gate, corta el ruido de fondo entre frases
         │
         ▼
   Carla:audio-out1 ──► system:playback_1
   Carla:audio-out2 ──► system:playback_2

system:midi_capture_2 (controlador MIDI) ──► Carla:events-in
```

### Parámetros exactos del Calf Filter
| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| Frequency | 100 Hz | Frecuencia de corte |
| Mode | 3 | Paso alto 12 dB/oct |
| Resonance | 0.707 | Q neutro (Butterworth, sin pico) |
| Inertia | 20 ms | Suavizado al mover el filtro |
| Input/Output Gain | 1.0 | Sin cambio de ganancia |

### Parámetros exactos del Calf Gate
| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| Threshold | 0.125 (−18 dB) | Nivel por debajo del cual se cierra el gate |
| Ratio | 2 | Reducción moderada (no corte total) |
| Attack | ~5 ms | Apertura rápida al detectar señal |
| Release | ~174 ms | Cierre lento para no cortar cola de voz |
| Max Gain Reduction | −42 dB (0.0078) | Atenuación máxima cuando el gate está cerrado |
| Knee | 2.83 | Transición suave (soft knee) |
| Detection | Peak | Detección por pico |
| Stereo Link | Off | Procesado independiente por canal |

### Notas de conexión JACK
- El micro (`system:capture_1`) se duplica en ambos canales de entrada de Carla para funcionar en mono.
- El controlador MIDI está en `system:midi_capture_2` (no en `midi_capture_1`).
- Al añadir plugins nuevos en este template, conectar siempre antes de `Audio Output` en el patchbay interno de Carla.

---

---

## LV2

Los bundles LV2 se encuentran en `/usr/lib/lv2/`.

### Efectos de Dinámica
| Plugin | Descripción |
|--------|-------------|
| `ZamComp.lv2` | Compresor mono de un solo band con controles estándar (threshold, ratio, attack, release) |
| `ZamCompX2.lv2` | Compresor estéreo doble de la suite ZAM |
| `ZaMultiComp.lv2` / `ZaMultiCompX2.lv2` | Compresor multibanda (mono/estéreo) |
| `ZamGate.lv2` / `ZamGateX2.lv2` | Noise gate (mono/estéreo) |
| `ZamAutoSat.lv2` | Saturador automático / limitador suave |
| `ZaMaximX2.lv2` | Maximizador estéreo (limiter de brickwall) |
| `ZamNoise.lv2` | Reducción de ruido |
| `ZamDynamicEQ.lv2` | Ecualizador dinámico |
| `sc1-swh.lv2` / `sc2-swh.lv2` / `sc3-swh.lv2` / `sc4-swh.lv2` | Compresores SC (Steve Harris) serie clásica |
| `se4-swh.lv2` | Expansor/gate stereo (serie SC) |
| `dyson_compress-swh.lv2` | Compresor Dyson |
| `fast_lookahead_limiter-swh.lv2` | Limitador lookahead rápido |
| `hard_limiter-swh.lv2` | Limitador hard |
| `lookahead_limiter-swh.lv2` / `lookahead_limiter_const-swh.lv2` | Limitadores lookahead |
| `satan_maximiser-swh.lv2` | Maximizador/saturador agresivo |
| `gate-swh.lv2` | Noise gate simple |
| `darc.lv2` | Compresor/reductor de rango dinámico |
| `dpl.lv2` | Limitador de pico dinámico |
| `envfollower.lv2` | Seguidor de envolvente |

### Ecualizadores y Filtros
| Plugin | Descripción |
|--------|-------------|
| `ZamEQ2.lv2` | EQ paramétrico de 2 bandas |
| `ZamGEQ31.lv2` | Ecualizador gráfico de 31 bandas |
| `3BandEQ.lv2` | EQ de 3 bandas simple |
| `3BandSplitter.lv2` | Divisor de frecuencias en 3 bandas |
| `fil4.lv2` | EQ paramétrico de 4 bandas de calidad |
| `mbeq-swh.lv2` | EQ multibanda (14 bandas) |
| `single_para-swh.lv2` | Filtro paramétrico de 1 banda |
| `triple_para-swh.lv2` | EQ paramétrico de 3 bandas |
| `highpass_iir-swh.lv2` / `lowpass_iir-swh.lv2` | Filtros paso-alto/bajo IIR |
| `bandpass_iir-swh.lv2` / `bandpass_a_iir-swh.lv2` | Filtros paso-banda IIR |
| `butterworth-swh.lv2` | Filtro Butterworth |
| `svf-swh.lv2` | Filtro de variable de estado (SVF) |
| `ls_filter-swh.lv2` | Filtro shelving (graves/agudos) |
| `dj_eq-swh.lv2` | EQ estilo DJ de 3 bandas |
| `hermes_filter-swh.lv2` | Filtro multimodal Hermes |
| `sapistaEQv2.lv2` | EQ paramétrico avanzado |
| `fomp.lv2` | Colección de filtros de Fons Adriaensen |
| `fat1.lv2` | Afinador/corrector de pitch automático |

### Reverb y Espacialización
| Plugin | Descripción |
|--------|-------------|
| `ZamVerb.lv2` | Reverb de placa ZAM |
| `ZamHeadX2.lv2` | Simulación HRTF binaural (cabeza estéreo) |
| `MaFreeverb.lv2` | Reverb Freeverb (algoritmo Schroeder-Moorer) |
| `MaGigaverb.lv2` | Reverb de cola larga, espacios grandes |
| `MVerb.lv2` | Reverb de alta calidad (basado en MVerb) |
| `gverb-swh.lv2` | Reverb GVerb, salas grandes |
| `plate-swh.lv2` | Reverb de placa clásica |
| `ir.lv2` | Reverb de convolución (impulse response) |
| `convo.lv2` | Convolución genérica |
| `TAL-Reverb.lv2` / `TAL-Reverb-2.lv2` / `TAL-Reverb-3.lv2` | Reverbs TAL-Audio, distintas épocas/sabores |
| `lushlife.lv2` | Reverb exuberante de cola larga |
| `matrix_spatialiser-swh.lv2` | Espacializador de matrix |
| `surround_encoder-swh.lv2` | Codificador de sonido surround |
| `PingPongPan.lv2` | Panning ping-pong estéreo |
| `balance.lv2` | Balance estéreo simple |

### Delay y Modulación de Tiempo
| Plugin | Descripción |
|--------|-------------|
| `ZamDelay.lv2` | Delay mono con feedback |
| `TAL-Dub-3.lv2` | Delay estilo dub (tape echo) |
| `bentdelay.lv2` | Delay con pitch bend |
| `delay-swh.lv2` | Delay simple |
| `fad_delay-swh.lv2` | Delay con desvanecimiento |
| `mod_delay-swh.lv2` | Delay modulado |
| `tape_delay-swh.lv2` | Simulación de delay de cinta |
| `lcr_delay-swh.lv2` | Delay Left-Center-Right |
| `revdelay-swh.lv2` | Delay con señal invertida (reverse delay) |
| `delayorama-swh.lv2` | Multi-tap delay (hasta 128 taps) |
| `comb-swh.lv2` | Filtro comb (resonador) |
| `allpass-swh.lv2` | Filtro all-pass |
| `simple_comb-swh.lv2` | Filtro comb simple |

### Chorus, Flanger y Phaser
| Plugin | Descripción |
|--------|-------------|
| `flanger-swh.lv2` | Flanger clásico |
| `retro_flange-swh.lv2` | Flanger retro/vintage |
| `giant_flange-swh.lv2` | Flanger de rango muy amplio |
| `dj_flanger-swh.lv2` | Flanger estilo DJ |
| `phasers-swh.lv2` | Phaser (varias topologías) |
| `multivoice_chorus-swh.lv2` | Chorus multivoz |
| `TAL-Filter.lv2` / `TAL-Filter-2.lv2` | Filtro modulado con LFO (auto-wah/envelope) |
| `invada.lv2` | Suite Invada: chorus, phaser, tremolo, cabinete |

### Distorsión y Saturación
| Plugin | Descripción |
|--------|-------------|
| `ZamTube.lv2` | Simulación de saturación de válvula/tubo |
| `ZamPhono.lv2` | Simulación de phono/vinilo |
| `ZamAutoSat.lv2` | Saturador automático |
| `chebstortion-swh.lv2` | Distorsión por polinomios de Chebyshev |
| `crossover_dist-swh.lv2` | Distorsión de cruce (crossover distortion) |
| `diode-swh.lv2` | Saturación de diodo |
| `foldover-swh.lv2` | Distorsión por plegado de onda (wavefold) |
| `shaper-swh.lv2` | Waveshaper genérico |
| `sinus_wavewrapper-swh.lv2` | Wrapping sinusoidal de onda |
| `foverdrive-swh.lv2` | Overdrive suave |
| `valve-swh.lv2` / `valve_rect-swh.lv2` | Simulación de válvula/rectificador |
| `SoulForce.lv2` | Distorsión/saturación "soul force" |
| `cheapdist.lv2` | Distorsión barata/lo-fi |
| `mod-bigmuff.lv2` | Emulación Big Muff Pi (fuzz) |
| `mod-ds1.lv2` | Emulación Boss DS-1 (distorsión) |
| `wolf-shaper.lv2` | Waveshaper con curva editable |
| `Temper.lv2` | Distorsión de clip digital |
| `mod-caps-Saturate.lv2` | Saturador CAPS |
| `mod-caps-ToneStack.lv2` | Emulación de tonestack de amplificador |
| `mod-caps-AmpVTS.lv2` | Simulación de amplificador de guitarra (vintage) |
| `mod-caps-CabinetIII.lv2` / `mod-caps-CabinetIV.lv2` | Simulación de cabina/speaker |
| `mod-caps-CEO.lv2` | Saturador CEO (overdriven amp) |
| `mod-caps-Spice.lv2` / `mod-caps-SpiceX2.lv2` | Distorsión tipo SPICE |
| `mod-caps-Fractal.lv2` | Distorsión fractal |
| `hip2b.lv2` | Exciter/enhancer de altas frecuencias |

### Pitch Shifting y Afinación
| Plugin | Descripción |
|--------|-------------|
| `MaPitchshift.lv2` | Pitch shifter de uso general |
| `rubberband.lv2` | Pitch shift y time stretch de alta calidad (Rubber Band) |
| `am_pitchshift-swh.lv2` | Pitch shift por AM (amplitude modulation) |
| `pitch_scale-swh.lv2` | Escalado de pitch simple |
| `rate_shifter-swh.lv2` | Shifter de tasa de muestreo |
| `mod-capo.lv2` / `mod-supercapo.lv2` | Pitch shift estilo capo de guitarra |
| `mod-harmonizer.lv2` / `mod-harmonizer2.lv2` / `mod-harmonizercs.lv2` | Armonizadores pitch shift |
| `mod-superwhammy.lv2` | Pitch shift tipo whammy pedal |
| `CycleShifter.lv2` | Shifter de ciclo de onda |
| `bode_shifter-swh.lv2` / `bode_shifter_cv-swh.lv2` | Frequency shifter (no pitch shift) estilo Bode |
| `fat1.lv2` | Corrección de pitch automática (autotune) |
| `tuna.lv2` | Afinador de instrumento |

### Vocoder y Procesamiento de Voz
| Plugin | Descripción |
|--------|-------------|
| `vocoder.lv2` | Vocoder clásico de bandas de filtros |
| `vocproc.lv2` | Procesador vocal (pitch correction + vocoder) |
| `TAL-Vocoder-2.lv2` | Vocoder TAL de alta calidad |
| `karaoke-swh.lv2` | Eliminador de voz central (karaoke) |
| `mod-caps-Scape.lv2` | Efectos de paisaje sonoro/vocal |

### Granular y Efectos Especiales
| Plugin | Descripción |
|--------|-------------|
| `ZamGrains.lv2` | Síntesis granular |
| `gong-swh.lv2` / `gong_beater-swh.lv2` | Simulación física de gong |
| `wave_terrain-swh.lv2` | Síntesis de terreno de onda (wave terrain) |
| `ringmod-swh.lv2` | Modulación de anillo |
| `decimator-swh.lv2` | Decimador/bit crusher (lo-fi) |
| `MaBitcrush.lv2` | Bit crusher |
| `smooth_decimate-swh.lv2` | Decimación suavizada |
| `harmonic_gen-swh.lv2` | Generador de armónicos |
| `hilbert-swh.lv2` | Transformada de Hilbert (phase quadrature) |
| `transient-swh.lv2` | Diseñador de transientes |
| `powercut.lv2` / `powerup.lv2` | Corte/amplificación dinámica |
| `vynil-swh.lv2` | Simulación de vinilo (scratches, crackles) |
| `mod-caps-Click.lv2` | Generador de clicks |
| `mod-caps-Narrower.lv2` / `mod-caps-Wider.lv2` | Narrador/ensanchador de imagen estéreo |
| `mod-caps-HaasEnhancer` (via invada) | Ensanchador Haas |
| `BShapr.lv2` | Secuenciador de formas de envoltura (bender/shaper) |
| `morph.lv2` | Morphing entre señales |
| `onsettrigger.lv2` | Detector de onset/ataque |

### Utilidades y Enrutamiento
| Plugin | Descripción |
|--------|-------------|
| `balance.lv2` | Balance L/R |
| `matrix_ms_st-swh.lv2` / `matrix_st_ms-swh.lv2` | Conversión Mid/Side ↔ estéreo |
| `xfade-swh.lv2` / `xfade.lv2` | Crossfade entre señales |
| `split-swh.lv2` | Divisor de señal |
| `matrixmixer.lv2` | Mezclador matricial |
| `mixtri.lv2` | Mezcla triangular |
| `stereoroute.lv2` | Enrutamiento estéreo |
| `nodelay.lv2` | Compensación de latencia |
| `dc_remove-swh.lv2` | Eliminador de componente DC |
| `declip-swh.lv2` | Desclipador |
| `sifter-swh.lv2` | Sifter (sample reordering) |
| `amp-swh.lv2` | Amplificador simple (ganancia) |
| `AmplitudeImposer.lv2` | Imposición de amplitud (seguidor de envolvente aplicado) |
| `controlfilter.lv2` | Filtro de señal de control |

### Instrumentos / Sintetizadores LV2
| Plugin | Descripción |
|--------|-------------|
| `Helm.lv2` | Sintetizador polífónico substractivo con LFOs, filtros, arpeggiator |
| `Surge.lv2` | Surge Synthesizer: substractivo/wavetable/FM avanzado |
| `synthv1.lv2` | Sintetizador substractivo analógico virtual |
| `samplv1.lv2` | Sampler LV2 |
| `padthv1.lv2` | Sintetizador PAD (algoritmo PADsynth) |
| `Nekobi.lv2` | Sintetizador monofonico basado en TB-303 |
| `Kars.lv2` | Sintetizador de cuerdas pulsadas (Karplus-Strong) |
| `TAL-NoiseMaker.lv2` | Sintetizador virtual analógico (3 osciladores, filtro ladder) |
| `b_synth` | Sintetizador de órgano Hammond con tonewheel |
| `b_whirl` | Simulación de altavoz rotatorio Leslie |
| `casynth.lv2` | Sintetizador CA (Cellular Automata) |
| `linuxsampler.lv2` | LinuxSampler: sampler de SFZ/GIG |
| `mod-2voices.lv2` | Síntesis de 2 voces para efectos de pitch |
| `mod-caps-Monosynth.lv2` | Monosynth CAPS |
| `mod-caps-White.lv2` | Generador de ruido blanco |
| `analogue_osc-swh.lv2` / `fm_osc-swh.lv2` | Osciladores básicos |

### Calf LV2 (bundle `calf.lv2`)
Suite completa de plugins:
| Plugin | Descripción |
|--------|-------------|
| `Reverb` | Reverb de sala algorítmica |
| `Vocoder` | Vocoder de bandas |
| `Fluidsynth` | Reproductor de soundfonts SF2 |
| `Organ` | Órgano Hammond virtual |
| `Wavetable` | Sintetizador wavetable |
| `Monosynth` | Sintetizador monofonico |
| `Compressor` / `MonoCompressor` / `SidechainCompressor` | Compresores (varios modos) |
| `MultibandCompressor` | Compresor multibanda |
| `Gate` / `SidechainGate` | Gates con y sin sidechain |
| `Limiter` / `SidechainLimiter` / `MultibandLimiter` | Limitadores |
| `Equalizer5Band/8Band/12Band/30Band` | EQs paramétricos de distintas bandas |
| `Filter` / `Filterclavier` | Filtros modulables |
| `EnvelopeFilter` | Filtro de envolvente (auto-wah) |
| `Chorus` / `MultiChorus` | Chorus mono y multi-voz |
| `Flanger` | Flanger |
| `Phaser` | Phaser |
| `Rotary Speaker` | Altavoz rotatorio (Leslie) |
| `Deesser` | De-esser |
| `VintageDelay` | Delay vintage |
| `ReverseDelay` | Delay inverso |
| `Analyzer` | Analizador de espectro |
| `TapeSimulator` | Simulación de cinta |
| `Saturator` | Saturador |
| `Vinyl` | Simulación de vinilo |
| `Pitch` | Pitch shifter |
| `RingModulator` | Modulador de anillo |
| `TransientDesigner` | Diseñador de transientes |
| `BassEnhancer` / `Exciter` | Realzador de graves/agudos |
| `HaasEnhancer` / `MultiSpread` | Ensanchadores estéreo |
| `XOver2Band/3Band/4Band` | Divisores de frecuencia |
| `CompensationDelay` | Delay de compensación de latencia |
| `Pulsator` | Tremolo/pulsador |
| `Crusher` | Bit crusher |
| `Emphasis` | Pre/de-énfasis |
| `Stereo Tools` | Herramientas estéreo completas |

### LSP Plugins LV2 (`lsp-plugins.lv2`) — Suite Profesional
El bundle incluye ~191 plugins cubriendo:
- **Compresores**: mono, stereo, LR, MS, con sidechain, multibanda
- **Expansores/Gates**: mono, stereo, LR, MS, con sidechain, multibanda
- **Limitadores**: mono, stereo, multibanda, con sidechain
- **EQs**: paramétrico x8/x16/x32 (mono/stereo/LR/MS), gráfico x16/x32
- **Delays**: articulado, de compensación, slap, multi-tap
- **Reverb**: por impulso (IR), room builder
- **Chorus / Flanger / Phaser**: mono y estéreo
- **Compresor dinámico / Procesador dinámico**: completo
- **Clipper**: mono y stereo, multibanda
- **Sampler**: mono y estéreo
- **Analizadores**: espectro x1/x2/x4/x8/x12/x16
- **Herramientas**: A/B tester, autogain, loudness comp, phase detector, profiler

---

## LADSPA

Los plugins LADSPA se encuentran en `/usr/lib/ladspa/` (y algunos en `~/.ladspa/`).

### Colección SWH (Steve Harris) — LADSPA clásicos
La mayoría de los plugins LADSPA son versiones LADSPA de los mismos plugins SWH presentes en LV2. Incluyen:
- Compresores: `sc1_1425.so`, `sc2_1426.so`, `sc3_1427.so`, `sc4_1882.so`, `sc4m_1916.so`
- Gates: `gate_1410.so`
- Limitadores: `fast_lookahead_limiter_1913.so`, `hard_limiter_1413.so`
- EQs/Filtros: `dj_eq_1901.so`, `mbeq_1197.so`, `single_para_1203.so`, `triple_para_1204.so`
- Filtros IIR: `highpass_iir_1890.so`, `lowpass_iir_1891.so`, `bandpass_iir_1892.so`, `butterworth_1902.so`
- Reverbs: `gverb_1216.so`, `plate_1423.so`
- Delays: `delay_1898.so`, `tape_delay_1211.so`, `revdelay_1605.so`, `delayorama_1402.so`
- Chorus/Flanger/Phaser: `flanger_1191.so`, `phasers_1217.so`, `multivoice_chorus_1201.so`
- Distorsión: `valve_1209.so`, `chebstortion_1430.so`, `diode_1185.so`, `foldover_1213.so`
- Pitch: `am_pitchshift_1433.so`, `pitch_scale_1193.so`
- Modulación: `ringmod_1188.so`, `hilbert_1440.so`
- Utilidades: `matrix_ms_st_1421.so`, `dc_remove_1207.so`, `declip_1195.so`

### TAP Plugins LADSPA
| Plugin | Descripción |
|--------|-------------|
| `tap_reverb.so` | Reverb algorítmica de alta calidad |
| `tap_echo.so` | Eco/delay |
| `tap_doubler.so` | Doblador de señal (stereo widening) |
| `tap_chorusflanger.so` | Chorus/flanger combinado |
| `tap_tremolo.so` | Tremolo |
| `tap_vibrato.so` | Vibrato |
| `tap_autopan.so` | Auto-panner |
| `tap_eq.so` / `tap_eqbw.so` | EQ gráfico / banda ancha |
| `tap_dynamics_m.so` / `tap_dynamics_st.so` | Dinámica mono/estéreo |
| `tap_limiter.so` | Limitador |
| `tap_deesser.so` | De-esser |
| `tap_pitch.so` | Pitch shifter |
| `tap_pinknoise.so` | Generador de ruido rosa |
| `tap_tubewarmth.so` | Saturación de tubo (warmth) |
| `tap_sigmoid.so` | Saturación sigmoidal |
| `tap_reflector.so` | Efecto reflector/resonador |
| `tap_rotspeak.so` | Altavoz rotatorio (Leslie) |

### CMT (Computer Music Toolkit) — `cmt.so`
Plugin con múltiples efectos: osciladores, filtros, compresores, delays, generadores de señal.

### Invada Studio — `inv_*.so`
| Plugin | Descripción |
|--------|-------------|
| `inv_compressor.so` | Compresor Invada |
| `inv_erreverb.so` | Reverb ER (early reflections) |
| `inv_filter.so` | Filtros Invada |
| `inv_input.so` | Preprocesador de entrada |
| `inv_tube.so` | Simulación de tubo Invada |

### Otros LADSPA notables
| Plugin | Descripción |
|--------|-------------|
| `autotalent.so` | Corrección de pitch automática (autotune) |
| `autowah.so` | Auto-wah / filtro de envolvente |
| `GSnap.so` (~/.ladspa) | Snap de pitch (corrección de afinación) |
| `MVerb-ladspa.so` | Reverb MVerb |
| `MaBitcrush-ladspa.so` | Bit crusher |
| `MaFreeverb-ladspa.so` | Reverb Freeverb |
| `MaGigaverb-ladspa.so` | Reverb Gigaverb |
| `MaPitchshift-ladspa.so` | Pitch shifter |
| `PingPongPan-ladspa.so` | Panning ping-pong |
| `SoulForce-ladspa.so` | Saturación/distorsión Soul Force |
| `ZamComp-ladspa.so` | Compresor ZAM |
| `ZamGate-ladspa.so` | Gate ZAM |
| `ZamNoise-ladspa.so` | Reducción de ruido ZAM |
| `ZamTube-ladspa.so` | Saturación de tubo ZAM |
| `ZamEQ2-ladspa.so` | EQ paramétrico ZAM |
| `ZamDelay-ladspa.so` | Delay ZAM |
| `ZamGEQ31-ladspa.so` | EQ gráfico 31 bandas ZAM |
| `ZamGrains-ladspa.so` | Granular ZAM |
| `ZamDynamicEQ-ladspa.so` | EQ dinámico ZAM |
| `ZaMultiCompX2-ladspa.so` | Compresor multibanda estéreo ZAM |
| `ZaMaximX2-ladspa.so` | Maximizador ZAM |
| `3BandEQ-ladspa.so` | EQ 3 bandas |
| `3BandSplitter-ladspa.so` | Divisor 3 bandas |
| `vocoder_1337.so` | Vocoder de bandas |
| `vynil_1905.so` | Simulación de vinilo |
| `zita-reverbs.so` | Suite de reverbs Zita de alta calidad |
| `lsp-plugins-ladspa.so` | Suite LSP completa en formato LADSPA |
| `blvco.so` / `vco_sawpulse.so` | Osciladores VCO analógicos |
| `mvchpf24.so` / `mvclpf24.so` | Filtros Moog-style (Victor Lazzarini) |
| `stereo-plugins.so` | Herramientas de imagen estéreo |
| `cs_chorus.so` / `cs_phaser.so` | Chorus y phaser CS |
| `gsm_1215.so` | Codificador GSM (efecto de teléfono móvil) |
| `gmsynth.lv2/gmsynth.so` (~/.ladspa) | General MIDI synthesizer |

---

## VST2

Los plugins VST2 se encuentran en `/usr/lib/vst/`.

### Plugins individuales VST2
| Plugin | Descripción |
|--------|-------------|
| `helm.so` | Sintetizador polífónico completo (equivalente al LV2) |
| `Surge.so` | Surge Synthesizer VST2 |
| `SoulForce-vst.so` | Distorsión/saturación Soul Force |
| `AIDA-X-vst2.so` | Neural amp modeler (modelos de IA de amplificadores) |
| `ZamEQ2-vst.so` | EQ paramétrico ZAM |
| `ZamTube-vst.so` | Saturación de tubo ZAM |
| `ZamDynamicEQ-vst.so` | EQ dinámico ZAM |
| `ZaMaximX2-vst.so` | Maximizador estéreo ZAM |
| `ZamDelay-vst.so` | Delay ZAM |
| `ZamNoise-vst.so` | Reducción de ruido ZAM |
| `ZamVerb-vst.so` | Reverb ZAM |
| `ZamGEQ31-vst.so` | EQ gráfico 31 bandas ZAM |
| `ZamHeadX2-vst.so` | HRTF binaural ZAM |
| `MVerb-vst.so` | Reverb MVerb |
| `MaBitcrush-vst.so` | Bit crusher |
| `MaFreeverb-vst.so` | Reverb Freeverb |
| `MaGigaverb-vst.so` | Reverb Gigaverb |
| `MaPitchshift-vst.so` | Pitch shifter |
| `3BandEQ-vst.so` | EQ 3 bandas |
| `3BandSplitter-vst.so` | Divisor 3 bandas |
| `PingPongPan-vst.so` | Panning ping-pong |
| `AmplitudeImposer-vst.so` | Imposición de amplitud |
| `CycleShifter-vst.so` | Cycle shifter |
| `Kars-vst.so` | Karplus-Strong VST2 |
| `Nekobi-vst.so` | TB-303 VST2 |
| `TAL-Reverb.so` / `TAL-Reverb-2.so` / `TAL-Reverb-3.so` | Reverbs TAL |
| `TAL-Dub-3.so` | Delay dub TAL |
| `TAL-Filter.so` / `TAL-Filter-2.so` | Filtros modulados TAL |
| `TAL-NoiseMaker.so` | Sintetizador TAL VST2 |
| `TAL-Vocoder-2.so` | Vocoder TAL VST2 |
| `glBars-vst.so` | Visualizador de barras GL |
| `b_whirl.lv2.so` | Leslie rotatorio (wrapper LV2→VST) |
| `b_synth.lv2.so` | Órgano Hammond (wrapper LV2→VST) |
| `fat1.lv2.so` | Autotune fat1 (wrapper LV2→VST) |
| `fil4.lv2.so` | EQ paramétrico fil4 (wrapper LV2→VST) |
| `balance.lv2.so` | Balance estéreo (wrapper LV2→VST) |
| `mod-bigmuff.lv2.so` | Big Muff fuzz (wrapper) |
| `mod-ds1.lv2.so` | Boss DS-1 (wrapper) |
| `mod-harmonizer.lv2.so` / `mod-harmonizer2.lv2.so` / `mod-harmonizercs.lv2.so` | Armonizadores (wrappers) |
| `mod-capo.lv2.so` / `mod-supercapo.lv2.so` | Capo/pitch shifter (wrappers) |
| `mod-superwhammy.lv2.so` | Whammy pedal (wrapper) |
| `mod-drop.lv2.so` | Drop tune (wrapper) |
| `mod-2voices.lv2.so` | 2 voces pitch (wrapper) |

### Carla VST2 (`carla.vst/`)
Bridge/host de plugins: permite cargar plugins LADSPA, LV2, VST dentro de un host VST. Incluye CarlaRack, CarlaPatchbay en distintas configuraciones de canales.

### LSP Plugins VST2 (`lsp-plugins.vst/`)
Suite completa (misma que LV2) en formato VST2. Incluye todos los compresores, EQs, delays, reverbs, gates, limitadores, analizadores, etc. en variantes mono/stereo/LR/MS.

---

## VST3

Los bundles VST3 se encuentran en `/usr/lib/vst3/`.

| Bundle | Descripción |
|--------|-------------|
| `3BandEQ.vst3` | EQ de 3 bandas |
| `3BandSplitter.vst3` | Divisor de 3 bandas de frecuencia |
| `AIDA-X.vst3` | Neural amp modeler (IA para simulación de amplificadores) |
| `AmplitudeImposer.vst3` | Imposición de amplitud |
| `CycleShifter.vst3` | Cycle shifter de frecuencia |
| `glBars.vst3` | Visualizador de espectro en barras OpenGL |
| `Kars.vst3` | Sintetizador Karplus-Strong (cuerdas pulsadas) |
| `lsp-plugins.vst3` | Suite LSP completa en VST3 |
| `MaBitcrush.vst3` | Bit crusher / reducción de bit depth |
| `MaFreeverb.vst3` | Reverb Freeverb |
| `MaGigaverb.vst3` | Reverb Gigaverb (colas largas) |
| `MaPitchshift.vst3` | Pitch shifter |
| `MVerb.vst3` | Reverb MVerb de alta calidad |
| `Nekobi.vst3` | Sintetizador basado en TB-303 |
| `PingPongPan.vst3` | Panning ping-pong estéreo |
| `ProM.vst3` | Visualizador de fase/Lissajous (metering) |
| `SoulForce.vst3` | Distorsión/saturación Soul Force |
| `Surge.vst3` | Surge Synthesizer completo (wavetable/FM/substractivo) |
| `ZamAutoSat.vst3` | Saturador automático ZAM |
| `ZaMaximX2.vst3` | Maximizador estéreo ZAM |
| `ZamComp.vst3` | Compresor ZAM |
| `ZamCompX2.vst3` | Compresor estéreo ZAM |
| `ZamDelay.vst3` | Delay ZAM |
| `ZamDynamicEQ.vst3` | EQ dinámico ZAM |
| `ZamEQ2.vst3` | EQ paramétrico 2 bandas ZAM |
| `ZamGate.vst3` | Gate ZAM |
| `ZamGateX2.vst3` | Gate estéreo ZAM |
| `ZamGEQ31.vst3` | EQ gráfico 31 bandas ZAM |
| `ZamGrains.vst3` | Síntesis granular ZAM |
| `ZamHeadX2.vst3` | Simulación binaural HRTF ZAM |
| `ZamNoise.vst3` | Reducción de ruido ZAM |
| `ZamPhono.vst3` | Simulación de phono/vinilo ZAM |
| `ZamTube.vst3` | Saturación de tubo ZAM |
| `ZaMultiComp.vst3` | Compresor multibanda ZAM |
| `ZaMultiCompX2.vst3` | Compresor multibanda estéreo ZAM |
| `ZamVerb.vst3` | Reverb ZAM |

---

## Notas de uso

- **Para Carla**: los plugins LV2, LADSPA y VST2/VST3 se pueden cargar directamente como plugins en racks/patchbays de Carla.
- **Para procesamiento en cadena**: usar archivos `.carxp` de Carla presentes en el proyecto.
- **Plugins más completos para uso general**:
  - Compresor de calidad: `lsp-plugins` (compressor), `Calf Compressor`, `ZamComp`
  - Reverb de calidad: `zita-reverbs` (LADSPA), `ir.lv2` (convolución), `MVerb`, `Calf Reverb`
  - EQ de calidad: `lsp-plugins` para-equalizer, `fil4.lv2`, `Calf Equalizer`
  - Vocoder: `TAL-Vocoder-2`, `vocproc.lv2`, `Calf Vocoder`
  - Pitch shift: `rubberband.lv2`, `lsp-plugins` pitch shifter
  - Simulación de amplificador: `AIDA-X` (neural), `mod-caps-AmpVTS`, `ZamTube`

# Audit of the 64-case free-space optics seed

## Source and method

Source: `自由空间光学实验推理试题集_初版.html` in the repository root. This is an audit of that source as supplied, not an endorsement of every gold answer. Counts below were obtained by parsing its `article` elements, headings, tags, ordered task lists, and gold-answer lists. The source file was not changed. All descriptions in this audit are in English.

The file is a single standalone HTML page. It has eight numbered sections, each with eight cases (`1.1` through `8.8`), for 64 unique IDs. Each case has one prompt, one ordered task list, and one collapsible gold-answer list. There are 199 task bullets and 198 gold-answer bullets; 58 cases have three tasks, five have four, and one has five. The gold lists contain three bullets in 58 cases and four bullets in six. A one-to-one task/gold count is not a valid general scoring assumption: case 8.1 alone has five tasks but four broad gold bullets.

## Inventory

The English titles and summaries here are audit labels, not final case text.

| ID | English working title | Primary reasoning tested |
|---|---|---|
| 1.1 | Mirror rotation and far-field displacement | Twice-angle reflection and spot displacement. |
| 1.2 | Two-mirror, two-aperture alignment | Iterative position and direction alignment. |
| 1.3 | Parallel beam translation | Two-reflection dogleg geometry. |
| 1.4 | Beam-height lift | Periscope geometry and output-axis verification. |
| 1.5 | Folded delay line | Round-trip path and time-delay conversion. |
| 1.6 | Dichroic wavelength routing | Spectral, angle, and polarization response. |
| 1.7 | Half-wave plate and linear polarization | Polarization-angle transformation and circular-input exception. |
| 1.8 | Continuously adjustable attenuation | Wave plate, polarizing beam splitter, and beam disposal. |
| 2.1 | Lens focus scale | Gaussian focal spot estimate. |
| 2.2 | Fivefold beam expansion | Telescope focal-length ratio and focal-point distinction. |
| 2.3 | High-peak-power expansion and filtering | Internal-focus damage, nonlinear effects, and pinhole design. |
| 2.4 | Changing Rayleigh range | Waist, divergence, and depth-of-focus tradeoff. |
| 2.5 | Higher-order modes in cavity coupling | Spatial mode matching versus frequency tuning. |
| 2.6 | Circularizing an elliptical beam | Anamorphic optics and two-axis verification. |
| 2.7 | Aperture truncation | Gaussian clipping and diffraction consequences. |
| 2.8 | Simultaneously reducing size and divergence | Beam-parameter-product and etendue limit. |
| 3.1 | Single-lens conjugates | Thin-lens 2f imaging and parity. |
| 3.2 | Unity-magnification relay | 4f imaging and its Fourier plane. |
| 3.3 | Central stop at a Fourier plane | Suppressing low spatial frequencies. |
| 3.4 | Pinhole in the wrong plane | Image-plane selection versus Fourier filtering. |
| 3.5 | Spectrometer slit width | Throughput and resolution tradeoff. |
| 3.6 | Accessing object and pupil planes | Separate field and aperture stops. |
| 3.7 | Diffraction-limited lateral resolution | Rayleigh estimate and depth-of-focus cost. |
| 3.8 | Measuring far-field angular distribution | Mapping angle to a lens focal plane. |
| 4.1 | Circular polarization with a quarter-wave plate | Retardance, axis angle, and handedness. |
| 4.2 | Michelson displacement and fringes | Double-pass phase sensitivity. |
| 4.3 | Mach-Zehnder fringe drift | Environmental and source-noise diagnosis. |
| 4.4 | Single-pass sample phase measurement | Interferometer choice and stability. |
| 4.5 | White-light fringe visibility | Coherence-length and dispersion matching. |
| 4.6 | Limits of Sagnac disturbance rejection | Reciprocal versus nonreciprocal perturbations. |
| 4.7 | Fabry-Perot spatial mode matching | Gaussian mode overlap and alignment controls. |
| 4.8 | Polarization-based balanced detection | Turning small rotations into differential intensity. |
| 5.1 | Right-angle fluorescence collection | Excitation rejection through geometry. |
| 5.2 | Confocal Raman system | Spatial and spectral background rejection. |
| 5.3 | Weak absorption with a reference channel | Source-noise normalization and residual error. |
| 5.4 | Chopping and lock-in detection | Modulation frequency and synchronous detection. |
| 5.5 | Optical heterodyne beat | Difference-frequency photocurrent and polarization overlap. |
| 5.6 | Detector saturation hiding Raman signal | System dynamic range and troubleshooting. |
| 5.7 | Noise limits of balanced detection | Shot-noise scaling and high-power limits. |
| 5.8 | Background rejection for a narrow spectral line | Sequential geometric, filter, and spectral suppression. |
| 6.1 | Small refractive-index change in a transparent sample | Competing interferometer architectures and calibration. |
| 6.2 | Femtosecond pump-probe transmission | Delay range, time zero, and resolution budget. |
| 6.3 | Multipass gas absorption cell | Herriott-like path multiplication and constraints. |
| 6.4 | Second-harmonic generation | Focusing, phase matching, and wavelength separation. |
| 6.5 | Confocal fluorescence depth scanning | Pinhole conjugacy and sectioning tradeoff. |
| 6.6 | Sensitive interferometric displacement | Nanometer displacement and phase calibration. |
| 6.7 | Mode cleaning before interferometry | Beam-conditioning sequence and acceptance tests. |
| 6.8 | Measuring phase and intensity together | Complex-field recovery and cross-talk. |
| 7.1 | Unable to center both alignment apertures | Distinguishing alignment procedure from physical reachability. |
| 7.2 | Diffraction rings after beam expansion | Clipping, contamination, pinhole, aberration, and input mode. |
| 7.3 | Low interferometric contrast | Coherence, polarization, wavefront, power, and overlap. |
| 7.4 | Verifying fivefold expansion | Independent beam-size and propagation measurement. |
| 7.5 | Half-wave attenuation of circular light | Why a rotating half-wave plate is insufficient. |
| 7.6 | Lossless polarization purification | Passive-mode and degree-of-polarization limit. |
| 7.7 | No pump-probe transient | Structured fault isolation and independent time-zero test. |
| 7.8 | Tiny focus with infinite depth of focus | Rayleigh-range and divergence constraint. |
| 8.1 | Low-cost, free-space absorption measurement | A weak-signal architecture with drift rejection and calibration. |
| 8.2 | Imaging a weak phase object | Multiple phase-to-intensity or phase-recovery principles. |
| 8.3 | Free-space polarization microscopy | Recovering spatial birefringence from multiple analyzer states. |
| 8.4 | Subpicosecond nonlinear-response measurement | Pump-probe architecture, background, and causality controls. |
| 8.5 | Stable common-path interferometry | Encoding sample/reference and calibrating phase. |
| 8.6 | Collinear multiwavelength transport | Dichroic combination, separation, and wavelength checks. |
| 8.7 | High-dynamic-range scattering | Direct-beam rejection and stray-light control. |
| 8.8 | From science target to acceptance plan | Characterization, beam conditioning, and measurable criteria. |

## Distribution and coverage

| Seed difficulty label | Cases | Share |
|---|---:|---:|
| Basic | 15 | 23.4% |
| Intermediate | 20 | 31.3% |
| Advanced | 21 | 32.8% |
| Integrated | 8 | 12.5% |

| Seed case-type label | Cases |
|---|---:|
| Design | 25 |
| Prediction | 11 |
| Open design | 8 |
| Diagnosis | 7 |
| Estimation | 3 |
| Tradeoff | 3 |
| Boundary | 3 |
| Critique | 3 |
| Calibration | 1 |

The difficulty progression is largely section driven: section 1 is all basic, section 6 is all advanced, and section 8 is all integrated/open design. Sections 2–5 and 7 mix levels. The labels describe intended demand; they have not been independently calibrated with response data or time-to-solve measurements.

The strongest coverage is in beam geometry and Gaussian propagation, Fourier imaging, interferometry and polarization, weak-signal detection, system assembly, and diagnosis. The cases regularly ask for physical reasoning, architecture choices, calibration, and failure modes. Many cases test the same general habits—verify alignment, reject background optically, distinguish source drift from sample signal, and measure an acceptance criterion—which is useful reinforcement but limits topical breadth.

### Provisional reasoning and scoring distributions

These are case-level audit judgments, not labels supplied by the seed. Each case appears once in each of the two independent partitions below. **Quantitative-dominant** means the main evidence needed for a correct answer is a computed value, scaling relation, focal-length choice, fringe count, or equivalent closed mathematical result; a case with a minor calculation inside a broad design task remains **qualitative-dominant**. **Deterministic-dominant** means most required credit can plausibly be assigned by an automatic rule-based checker with normalized units, formulas, and a small list of equivalent closed answers. **Semantic-dominant** means most credit requires evaluating whether an explanation, design, diagnostic sequence, or verification plan meets a rubric. Semantic scoring can and should also be fully automated by a calibrated judge; it does not imply human grading.

| Partition | Cases | Share | Case IDs or rule |
|---|---:|---:|---|
| Quantitative-dominant | 11 | 17.2% | 1.1, 1.5, 1.7, 2.1, 2.2, 2.4, 3.1, 3.7, 4.2, 5.5, 6.2. |
| Qualitative-dominant | 53 | 82.8% | All other IDs; includes mixed cases 6.6 and 8.8 because their architecture and acceptance reasoning dominates. |
| Deterministic-dominant automatic scoring | 10 | 15.6% | 1.1, 1.5, 1.7, 2.1, 2.2, 2.4, 3.1, 3.7, 4.2, 5.5. |
| Semantic-dominant automatic scoring | 54 | 84.4% | All other IDs; 6.2 requires a numeric delay plus a complete pump-probe design. |

The quantitative boundary is provisional: 6.6 includes a precise phase-to-displacement formula, and 8.8 asks for a quantified acceptance example, but neither is primarily a calculation case. Conversely, section 2 includes several numerical givens whose requested outputs are qualitative. Only three cases carry the seed's explicit `estimation` tag, so that tag is not a measure of quantitative coverage. The deterministic estimate assumes the English rewrite resolves sign conventions, answer tolerances, and equivalent formulations identified below; without those fixes, even some of these ten cases need semantic adjudication.

## Corrections and clarifications before translation or scoring

| Priority | Cases | Issue and proposed resolution |
|---|---|---|
| High | 7.1 | The gold list gives “the two apertures are not collinear” as a possible reason for failure. Any two aperture centers define a line. Replace with an actual constraint: their line is incompatible with a third fixed reference, blocked by hardware, or outside the mirrors' steering range. If the hardware permits two independent steering degrees of freedom, two targets can usually be centered. |
| High | 8.1 | The fifth task asks for at least three acceptable alternative implementations; the four gold bullets neither enumerate nor distinguish three. Add three concretely different acceptable architectures and state their required controls. |
| High | 4.8 | A polarizing beam splitter and two detectors produce a first-order differential response to a small rotation only when the input/analyzer are biased near equal output powers (for example, 45 degrees). Add the operating point and balanced-gain calibration to the prompt or gold notes. |
| Medium | 1.2 | The gold answer assigns the first mirror to the near aperture and second to the far one as if their individual effects were independent. Their actual roles depend on the distances and layout; moving either steering mirror generally affects both positions. Frame the method as iterative two-plane alignment and require an explicitly described geometry. |
| Medium | 1.7 | “Rotates by 34 degrees” omits a sign/reference convention. For a chosen fast-axis angle, the output axis is the reflection of the input axis about that fast axis; 34 degrees is a magnitude. State a viewing direction and signed angle convention, or accept either sign if the transformation is correct. |
| Medium | 1.4 | Two downstream apertures establish a desired output line, but centering on unspecified apertures alone does not prove parallelism with the input. Define both aperture centers relative to the input direction or prescribe an angular measurement over known propagation distance. |
| Medium | 2.7 | “Several times the spot radius” does not define an acceptance criterion. For a circular Gaussian with radius `w = 4 mm` and aperture radius `a = 5 mm`, ideal centered clipping loses `exp[-2(a/w)^2]`, about 4.4% of power. State an allowable clipping loss and derive a minimum aperture radius; diffraction requirements may demand more clearance. |
| Medium | 5.7 | “Difference noise no longer decreases with power” is ambiguous: absolute shot-noise current grows approximately as the square root of photocurrent, while noise referred to a normalized signal decreases. Specify the plotted quantity and measurement bandwidth before scoring the trend. |
| Medium | 8.6 | “Completely separate” the two wavelengths is physically overstrong for finite filter extinction. Specify a tolerated cross-channel leakage or isolation ratio and a measurement for it. |
| Medium | 8.3 | Reconstructing birefringence axis and retardance from intensities has ambiguities and model dependence (axis periodicity, retardance wrapping, depolarization and diattenuation). State the sample model and required independent polarization measurements; allow solutions that explicitly resolve or bound degeneracies. |
| Low | 1.1 | The mirror is described as nearly normally illuminated, while the downstream screen geometry is not defined. State that the screen is normal to the nominal reflected ray and 2.0 m along it for the `L tan(2θ)` estimate. |
| Low | 2.1 | The ideal `λf/(πw)` result assumes an approximately collimated diffraction-limited Gaussian at the lens. State the beam-quality assumption or award credit for an `M²` qualification. |
| Low | 3.3 | A central opaque stop is a high-pass-like filter, but a real coherent image can exhibit ringing, sign changes, and strong dependence on stop size. Avoid grading a specific appearance beyond suppression of low spatial frequencies. |
| Low | 6.2 | The seed rounds the 500 ps span to about 75 mm of folded-stage travel and separately mentions negative-delay margin. The specified interval is -2 to 500 ps, so a more direct minimum is about 75.3 mm before setup margin. Accept either properly qualified result. |

The quantitative values in 1.1, 1.5, 2.1, 2.2, 2.4, 3.1, 3.7, 4.2, 5.5, 6.2, and 6.6 are otherwise consistent at their stated level of approximation. The audit did not find duplicate IDs or verbatim duplicate cases.

## Near-duplicates and ways to preserve their distinct purpose

| Cluster | Cases | Distinction worth making explicit |
|---|---|---|
| Alignment and beam conditioning | 1.2, 6.7, 7.1, 8.8 | Procedure, complete conditioning chain, failure diagnosis, and acceptance plan, respectively. |
| Expansion and mode quality | 2.2, 2.3, 2.6, 2.7, 7.2, 7.4 | Ideal design, damage-limited filtering, anamorphism, aperture sizing, ring diagnosis, and empirical calibration. |
| Gaussian invariants | 2.4, 2.8, 7.8 | Ordinary parameter scaling, beam-parameter-product impossibility, and focus/depth-of-focus impossibility. |
| Cavity coupling | 2.5, 4.7 | Diagnosing observed higher-order modes versus designing the matching controls and diagnostics. |
| Polarization attenuation | 1.7, 1.8, 7.5, 7.6 | Half-wave transformation, linear-input attenuation, circular-input counterexample, and unpolarized-input limit. |
| Interferometer stability and phase | 4.3, 4.4, 4.6, 6.1, 6.6, 8.5 | Drift diagnosis, single-pass topology, Sagnac caveat, index inference, displacement inference, and common-path synthesis. |
| Weak-signal detection | 5.3, 5.4, 5.6, 5.7, 5.8, 8.1, 8.7 | Reference normalization, modulation, saturation, noise floor, spectral background, whole-system absorption, and scatter dynamic range. |
| Pump-probe work | 6.2, 7.7, 8.4 | Quantitative system build, absent-signal diagnosis, and open ultrafast response design. |

These clusters should not be merged mechanically. They can be differentiated through the evidence the learner must produce: calculation, layout, fault tree, uncertainty estimate, or acceptance test.

## Gaps in the benchmark seed

1. **Measurements and uncertainty.** Few cases require numerical uncertainty propagation, calibration uncertainty, repeatability, confidence intervals, measurement bandwidth, or a noise budget tied to a detection limit. Add these where the claimed signals are `10^-4` or `10^-5` (5.3, 8.1) and where phase is converted to displacement or index (6.1, 6.6).
2. **Explicit experimental constraints.** Many design prompts omit available power, detector specifications, wavelength bandwidth, aperture budget, working distance, pulse energy at optics, and permissible losses. Keeping some problems open is appropriate, but scoring requires either a stated constraint set or points for identifying missing specifications.
3. **Safety and damage controls.** Case 1.8 addresses beam dumps and 2.3/6.4 discuss damage, but systematic high-power beam safety, open-beam containment, interlocks, and safe alignment are largely absent. These should be integrated into applicable design cases without turning every case into a checklist.
4. **Tolerance and sensitivity analysis.** There are few explicit perturbation calculations for mirror drift, lens decenter, angular misalignment, thermal drift, or finite extinction. These would complement the conceptual diagnosis cases.
5. **Traceable evidence and data interpretation.** Most cases are prose-only and provide no measured plots, images, spectra, or instrument readings. Data-based cases would test whether the learner can infer a cause from evidence rather than recite candidate causes.
6. **Bench realism beyond ideal scalar models.** Dispersion, chromatic focus, coating response, finite contrast, polarization changes at oblique reflection, aberration, and detector nonlinearity appear as mentions but are seldom quantified.
7. **Calibration case diversity.** Only 7.4 is labeled calibration, though calibration appears in many gold bullets. More cases could center on a reference standard, calibration curve, and independent verification.

## Scoring architecture implications

The seed's gold notes are useful answer outlines, but they are not yet executable grading rubrics. Most bullets combine several criteria and omit weights, tolerance bands, and disqualifying physics errors. Several prompts explicitly allow multiple valid optical architectures. A reliable scorer should therefore separate **required physical constraints**, **one of several acceptable implementations**, **verification evidence**, and **incorrect claims that invalidate the design**. The English version should give each criterion an ID and a score range, with example evidence and equivalent answers.

Rule-based grading is easiest for calculations with declared assumptions (1.1, 1.5, 2.1, 2.2, 2.4, 3.1, 3.7, 4.2, 5.5). Semantic automatic grading is needed for layout design because equivalent optical orderings and mirror geometries exist (1.2–1.4, 3.6, 4.4, 6.1–6.8). It is most demanding for open design and diagnosis (7.1–7.3, 7.7, all of section 8), where a keyword list would reward shallow enumeration and penalize novel sound solutions. For those cases, score whether the response makes testable predictions, respects constraints, and proposes discriminating checks in a plausible order. Calibrate the fully automated judge against a fixed set of exemplar responses and criterion-level decisions at different quality levels; an optional human audit may monitor drift and inspect disputed outcomes without becoming part of routine scoring.

Some cases request “at least N” causes or alternatives. Counting names alone is inadequate when synonyms or causally identical answers are listed. Define category-level distinctness and a minimum explanation for each item. Numerical responses need explicit units, significant-figure expectations, and permitted approximations. These changes can be made in English without carrying over the Chinese presentation or building bilingual infrastructure now.

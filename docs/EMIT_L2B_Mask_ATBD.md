## **Earth Surface Mineral dust source InvesTigation (EMIT)** 

# **EMIT L2B Algorithm: Masks** 

**Philip G. Brodrick**<sup>1</sup></br>
**Jake H. Lee**<sup>1</sup></br>
**Michael Kiper**<sup>1</sup></br>
**Winston Olson-Duvall**<sup>1</sup></br>
**Sarah R. Lundeen**<sup>1</sup></br>

<sup>1</sup>Jet Propulsion Laboratory, California Institute of Technology

**Version:** 1.0 </br>
**Release Date:** TBD </br>
**JPL- D-XXXXXX** </br>


Jet Propulsion Laboratory </br>
California Institute of Technology </br>
Pasadena, California 91109-8099 </br>

<div style="page-break-after: always;"></div>

**Change Log**
| Version | Date       | Comments |
|---------|------------|----------|
| 0.0     | YYYY-MM-DD | Initial Draft |

<div style="page-break-after: always;"></div>


## **1. Key Teammembers**

<div style="page-break-after: always;"></div>

## **2. Historical Context and Background on the EMIT Mission and its Instrumentation**

## **3. Algorithm Rationale**

## **4. Algorithm Implementation**

### **4.1 Input Data**

### **4.2 Theoretical Description**

### **4.3 Practical Considerations**

### **4.4 Output Data**

## **5. Calibration, uncertainty characterization and propagation, and validation**
We quantify prediction uncertainty directly from the model’s posterior class probabilities. Given the calibration curve on our [test set](https://zenodo.org/records/15833303/files/test_fids.csv) provided below, the model is near-perfectly calibrated given how close it is to a perfect linear fit. This means that the posterior probabilities reliably approximate the likelihood that a given spectra is of a specific class. Roughly, a given probability score will only be between an overconfidence of $2.2\%$ or underconfidence of $1.5\%$. 
<center><img src="figs/calibration-curve.png" alt="calibration curve" width="400"></center>

Thus, when interpreting the output probabilities, one can reliably infer that $f(x) ≈ P(class=c|x)$ where $f(•)$ is the model. 

## **6. Constraints and Limitations**
Given that this is a deep learning model trained on a (relatively) small, sparse set of imperfect human labels, it is bound to be an imperfect classifier. Specifically, as a quantitative measure, the model will provide an incorrect label when using the $P(0.51)$ threshold about $4\%$ of the time, using the labeled test set as ground truth. Some spectra types have been observed to be more difficult than others for our model to classify properly. Namely, these tend to be: 
- Scenes where there is a very fine haze.
- Regions in India and the South Asian subcontinent that are high in vegetation and aerosols.
- Pixel regions that intersect with the known artifact on the slit and instrument artifacts towards the focal plane array on the right edge.
- The model also exhibits higher entropy over bright plains and very dense, dark vegetative regions that don't have any cloud trace. 
    - These values tend to be below the $P(0.51)$ threshold, though, but nonetheless something to look out for.


Additionally, when interpreting the results of the model's posterior probabilites, it is important to know that the outputs are the likelihoods of if there is or is not a cloud within the pixel space. This is due to the fact that the model was trained on discrete, exclusive class labels. It is not a measure of how much cloud trace there is within the pixel space. I.e. $P(Cloud)=0.10$ means there is a $10\%$ chance that the pixel is a cloud pixel, not that $10\%$ of the measured relfectance is a cloud residual or from a cloud-class source.   

<div style="page-break-after: always;"></div>

## **References**




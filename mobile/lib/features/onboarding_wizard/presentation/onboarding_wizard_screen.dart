import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../documents/presentation/documents_providers.dart';
import '../../profile/domain/employee_profile.dart';
import '../../profile/presentation/profile_providers.dart';
import '../../services/domain/service_catalog.dart';
import '../../services/presentation/services_providers.dart';
import 'onboarding_wizard_providers.dart';

const _stepLabels = [
  'Personal',
  'Address & Territory',
  'Services',
  'Skills & Tools',
  'Documents',
  'Bank Details',
  'Review & Submit',
];

const _requiredDocuments = [
  ('aadhaar', 'Aadhaar / National ID Card', true),
  ('address_proof', 'Address Proof (Electricity Bill / Rent Agreement)', true),
  ('trade_cert', 'Trade / Vocational Certificate', false),
  ('bank_proof', 'Bank Proof (Cancelled Cheque / Passbook)', true),
];

/// The mobile Registration Wizard — mirrors the web app's 7-step onboarding
/// flow field-for-field against the same backend contract
/// (`PATCH /workforce/onboarding/draft/`, `POST /workforce/onboarding/documents/`,
/// `POST /workforce/onboarding/submit/`), so a registration can be started or
/// resumed interchangeably from web or mobile.
///
/// [initialStep] lets a correction-required re-entry jump straight to the
/// step containing the flagged section instead of wherever `onboarding_data.step`
/// last left off.
class OnboardingWizardScreen extends ConsumerStatefulWidget {
  const OnboardingWizardScreen({super.key, this.initialStep});

  final int? initialStep;

  @override
  ConsumerState<OnboardingWizardScreen> createState() => _OnboardingWizardScreenState();
}

class _OnboardingWizardScreenState extends ConsumerState<OnboardingWizardScreen> {
  bool _hydrated = false;
  int _currentStep = 1;
  bool _isSaving = false;
  String? _errorMessage;

  // Preserves any keys we don't have dedicated fields for (e.g. the
  // pre-seeded first_name/last_name/email/mobile_number in `personal`) so
  // saving a step never silently drops data written by the web app.
  Map<String, dynamic> _personalRaw = {};
  Map<String, dynamic> _addressRaw = {};
  Map<String, dynamic> _skillsRaw = {};
  Map<String, dynamic> _bankRaw = {};

  // Step 1 — Personal Information
  final _dobController = TextEditingController();
  String? _gender;
  final _emergencyNameController = TextEditingController();
  final _emergencyPhoneController = TextEditingController();

  // Step 2 — Address & Territory
  final _streetController = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();
  final _pincodeController = TextEditingController();
  double _serviceRadius = 10;

  // Step 3 — Services
  final Map<dynamic, Map<String, dynamic>> _selectedServices = {};

  // Step 4 — Skills & Tools
  final _experienceYearsController = TextEditingController();
  String? _vehicleType;
  final _licenseNumberController = TextEditingController();

  // Step 6 — Bank Details
  final _accountHolderController = TextEditingController();
  final _ifscController = TextEditingController();
  final _accountNumberController = TextEditingController();
  final _confirmAccountNumberController = TextEditingController();
  bool _obscureAccountNumber = true;

  // Step 7 — Review & Submit
  bool _declarationAccepted = false;

  @override
  void dispose() {
    _dobController.dispose();
    _emergencyNameController.dispose();
    _emergencyPhoneController.dispose();
    _streetController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _pincodeController.dispose();
    _experienceYearsController.dispose();
    _licenseNumberController.dispose();
    _accountHolderController.dispose();
    _ifscController.dispose();
    _accountNumberController.dispose();
    _confirmAccountNumberController.dispose();
    super.dispose();
  }

  void _hydrate(OnboardingData data) {
    if (_hydrated) return;
    _hydrated = true;

    _currentStep = widget.initialStep ?? data.step.clamp(1, 7);

    _personalRaw = data.section('personal');
    _dobController.text = (_personalRaw['dob'] as String?) ?? '';
    final genderValue = _personalRaw['gender'] as String?;
    _gender = (genderValue == 'male' || genderValue == 'female' || genderValue == 'other')
        ? genderValue
        : null;
    _emergencyNameController.text = (_personalRaw['emergencyName'] as String?) ?? '';
    _emergencyPhoneController.text = (_personalRaw['emergencyPhone'] as String?) ?? '';

    _addressRaw = data.section('address');
    _streetController.text = (_addressRaw['street'] as String?) ?? '';
    _cityController.text = (_addressRaw['city'] as String?) ?? '';
    _stateController.text = (_addressRaw['state'] as String?) ?? '';
    _pincodeController.text = (_addressRaw['pincode'] as String?) ?? '';
    final radius = _addressRaw['serviceRadius'];
    _serviceRadius = (radius is num ? radius.toDouble() : 10.0).clamp(5.0, 50.0);

    for (final svc in data.services) {
      final id = svc['id'];
      if (id == null) continue;
      _selectedServices[id] = {
        'id': id,
        'name': svc['name'] ?? '',
        'category': svc['category'] ?? '',
      };
    }

    _skillsRaw = data.section('skills');
    final years = _skillsRaw['experienceYears'];
    _experienceYearsController.text = years == null ? '' : '$years';
    final vehicle = _skillsRaw['vehicleType'] as String?;
    _vehicleType = (vehicle == 'two_wheeler' ||
            vehicle == 'four_wheeler' ||
            vehicle == 'bicycle' ||
            vehicle == 'public_transit')
        ? vehicle
        : null;
    _licenseNumberController.text = (_skillsRaw['licenseNumber'] as String?) ?? '';

    _bankRaw = data.section('bank');
    _accountHolderController.text = (_bankRaw['accountHolder'] as String?) ?? '';
    _ifscController.text = (_bankRaw['ifsc'] as String?) ?? '';
    // Deliberately not pre-filling accountNumber/confirmAccountNumber from a
    // resumed draft — the backend stores them as plaintext JSON with no
    // masking, so echoing them back into an editable field on resume would
    // needlessly re-expose a sensitive value already at rest. Re-entry is
    // one extra step, not a contract change (same fields, same endpoint).
  }

  Future<bool> _saveSection(int step, String key, dynamic value) async {
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });
    final ok = await ref
        .read(onboardingWizardControllerProvider.notifier)
        .saveStep(step: step, draftData: {key: value});
    if (!mounted) return ok;
    setState(() {
      _isSaving = false;
      if (!ok) _errorMessage = 'Could not save. Please check your connection and try again.';
    });
    return ok;
  }

  Future<void> _goNext() async {
    switch (_currentStep) {
      case 1:
        if (_dobController.text.trim().isEmpty) {
          setState(() => _errorMessage = 'Please enter your date of birth.');
          return;
        }
        final personal = {
          ..._personalRaw,
          'dob': _dobController.text.trim(),
          'gender': _gender ?? '',
          'emergencyName': _emergencyNameController.text.trim(),
          'emergencyPhone': _emergencyPhoneController.text.trim(),
        };
        if (!await _saveSection(2, 'personal', personal)) return;
        _personalRaw = personal;
        break;
      case 2:
        if (_streetController.text.trim().isEmpty ||
            _cityController.text.trim().isEmpty ||
            _pincodeController.text.trim().isEmpty) {
          setState(() => _errorMessage = 'Please complete your address details.');
          return;
        }
        final address = {
          ..._addressRaw,
          'street': _streetController.text.trim(),
          'city': _cityController.text.trim(),
          'state': _stateController.text.trim(),
          'pincode': _pincodeController.text.trim(),
          'serviceRadius': _serviceRadius.round(),
        };
        if (!await _saveSection(3, 'address', address)) return;
        _addressRaw = address;
        break;
      case 3:
        if (_selectedServices.isEmpty) {
          setState(() => _errorMessage = 'Please select at least one service you provide.');
          return;
        }
        if (!await _saveSection(4, 'services', _selectedServices.values.toList())) return;
        break;
      case 4:
        final skills = {
          ..._skillsRaw,
          'experienceYears': double.tryParse(_experienceYearsController.text.trim()) ?? 0,
          'vehicleType': _vehicleType ?? '',
          'licenseNumber': _licenseNumberController.text.trim(),
        };
        if (!await _saveSection(5, 'skills', skills)) return;
        _skillsRaw = skills;
        break;
      case 5:
        if (!await _saveSection(6, 'documents', const {})) return;
        break;
      case 6:
        final holder = _accountHolderController.text.trim();
        final ifsc = _ifscController.text.trim();
        final accountNumber = _accountNumberController.text.trim();
        final confirm = _confirmAccountNumberController.text.trim();
        if (holder.isEmpty || ifsc.isEmpty || accountNumber.isEmpty || confirm.isEmpty) {
          setState(() => _errorMessage = 'Please complete all bank detail fields.');
          return;
        }
        if (accountNumber != confirm) {
          setState(() => _errorMessage = 'Account numbers do not match.');
          return;
        }
        final bank = {
          ..._bankRaw,
          'accountHolder': holder,
          'ifsc': ifsc,
          'accountNumber': accountNumber,
          'confirmAccountNumber': confirm,
        };
        if (!await _saveSection(7, 'bank', bank)) return;
        _bankRaw = bank;
        break;
    }
    if (!mounted) return;
    setState(() {
      _errorMessage = null;
      if (_currentStep < 7) _currentStep += 1;
    });
  }

  Future<void> _goBack() async {
    if (_currentStep <= 1) return;
    setState(() => _errorMessage = null);
    final prev = _currentStep - 1;
    // Persist whatever's on the current step so nothing typed is lost, but
    // don't block backward navigation on validation.
    await _saveSection(_currentStep, _currentSectionKey(), _currentSectionValue());
    if (!mounted) return;
    setState(() => _currentStep = prev);
  }

  String _currentSectionKey() {
    switch (_currentStep) {
      case 1:
        return 'personal';
      case 2:
        return 'address';
      case 3:
        return 'services';
      case 4:
        return 'skills';
      case 6:
        return 'bank';
      default:
        return 'documents';
    }
  }

  dynamic _currentSectionValue() {
    switch (_currentStep) {
      case 1:
        return {
          ..._personalRaw,
          'dob': _dobController.text.trim(),
          'gender': _gender ?? '',
          'emergencyName': _emergencyNameController.text.trim(),
          'emergencyPhone': _emergencyPhoneController.text.trim(),
        };
      case 2:
        return {
          ..._addressRaw,
          'street': _streetController.text.trim(),
          'city': _cityController.text.trim(),
          'state': _stateController.text.trim(),
          'pincode': _pincodeController.text.trim(),
          'serviceRadius': _serviceRadius.round(),
        };
      case 3:
        return _selectedServices.values.toList();
      case 4:
        return {
          ..._skillsRaw,
          'experienceYears': double.tryParse(_experienceYearsController.text.trim()) ?? 0,
          'vehicleType': _vehicleType ?? '',
          'licenseNumber': _licenseNumberController.text.trim(),
        };
      case 6:
        return {
          ..._bankRaw,
          'accountHolder': _accountHolderController.text.trim(),
          'ifsc': _ifscController.text.trim(),
        };
      default:
        return const {};
    }
  }

  Future<void> _submit() async {
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });
    final ok = await ref.read(onboardingWizardControllerProvider.notifier).submit();
    if (!mounted) return;
    setState(() {
      _isSaving = false;
      if (!ok) {
        _errorMessage = 'Submission failed. Please check your connection and try again.';
      }
    });
    // On success the router's redirect gate picks up the fresh
    // registrationStatus ('submitted') automatically — no manual navigation.
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(employeeProfileProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Registration',
        showSearch: false,
        showNotifications: false,
        showAvatar: false,
      ),
      body: SafeArea(
        child: AsyncValueView<EmployeeProfile>(
          value: profileAsync,
          onRetry: () => ref.invalidate(employeeProfileProvider),
          builder: (context, profile) {
            _hydrate(profile.onboardingData);
            return Column(
              children: [
                _WizardProgressHeader(currentStep: _currentStep),
                if (_errorMessage != null)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.sm),
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      color: AppColors.error.tint,
                      border: Border.all(color: AppColors.error.tintBorder),
                      borderRadius: BorderRadius.circular(AppRadius.input),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: TextStyle(color: AppColors.error.onTint, fontSize: 13),
                    ),
                  ),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.lg,
                      AppSpacing.sm,
                      AppSpacing.lg,
                      AppSpacing.xl,
                    ),
                    child: _buildStep(profile),
                  ),
                ),
                _WizardFooter(
                  currentStep: _currentStep,
                  isSaving: _isSaving,
                  canSubmit: _currentStep == 7 && _declarationAccepted,
                  onBack: _isSaving ? null : _goBack,
                  onNext: _isSaving ? null : _goNext,
                  onSubmit: _isSaving ? null : _submit,
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildStep(EmployeeProfile profile) {
    switch (_currentStep) {
      case 1:
        return _buildPersonalStep();
      case 2:
        return _buildAddressStep();
      case 3:
        return _buildServicesStep();
      case 4:
        return _buildSkillsStep();
      case 5:
        return _buildDocumentsStep(profile);
      case 6:
        return _buildBankStep();
      default:
        return _buildReviewStep(profile);
    }
  }

  // ── Step 1 — Personal Information ─────────────────────────────────────────
  Widget _buildPersonalStep() {
    return _StepCard(
      icon: Icons.badge_outlined,
      title: '1. Personal Information',
      children: [
        _FieldLabel('Date of Birth', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _dobController,
          readOnly: true,
          decoration: _inputDecoration(hintText: 'YYYY-MM-DD', icon: Icons.calendar_today_outlined),
          onTap: () async {
            final now = DateTime.now();
            final initial = DateTime.tryParse(_dobController.text) ??
                DateTime(now.year - 25, now.month, now.day);
            final picked = await showDatePicker(
              context: context,
              initialDate: initial,
              firstDate: DateTime(1950),
              lastDate: DateTime(now.year - 16, now.month, now.day),
            );
            if (picked != null) {
              _dobController.text =
                  '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
              setState(() {});
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Gender', required: false),
        const SizedBox(height: 6),
        DropdownButtonFormField<String>(
          initialValue: _gender,
          decoration: _inputDecoration(hintText: 'Select gender', icon: Icons.person_outline),
          items: const [
            DropdownMenuItem(value: 'male', child: Text('Male')),
            DropdownMenuItem(value: 'female', child: Text('Female')),
            DropdownMenuItem(value: 'other', child: Text('Other')),
          ],
          onChanged: (value) => setState(() => _gender = value),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Emergency Contact Name', required: false),
        const SizedBox(height: 6),
        TextField(
          controller: _emergencyNameController,
          decoration: _inputDecoration(
            hintText: 'e.g. Priya (Spouse / Parent)',
            icon: Icons.person_pin_outlined,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Emergency Contact Phone', required: false),
        const SizedBox(height: 6),
        TextField(
          controller: _emergencyPhoneController,
          keyboardType: TextInputType.phone,
          decoration: _inputDecoration(hintText: '9876543211', icon: Icons.phone_outlined),
        ),
      ],
    );
  }

  // ── Step 2 — Address & Territory ────────────────────────────────────────
  Widget _buildAddressStep() {
    return _StepCard(
      icon: Icons.map_outlined,
      title: '2. Residential Address & Travel Territory',
      children: [
        _FieldLabel('Street Address', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _streetController,
          maxLines: 2,
          decoration: _inputDecoration(hintText: 'House / street / area', icon: Icons.home_outlined),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('City', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _cityController,
          decoration: _inputDecoration(hintText: 'City', icon: Icons.location_city_outlined),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('State', required: false),
        const SizedBox(height: 6),
        TextField(
          controller: _stateController,
          decoration: _inputDecoration(hintText: 'State', icon: Icons.map_outlined),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Pincode', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _pincodeController,
          keyboardType: TextInputType.number,
          decoration: _inputDecoration(hintText: 'Pincode', icon: Icons.pin_drop_outlined),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Service Travel Radius: ${_serviceRadius.round()} km', style: AppTypography.body),
        Slider(
          value: _serviceRadius,
          min: 5,
          max: 50,
          divisions: 9,
          activeColor: AppColors.primary,
          label: '${_serviceRadius.round()} km',
          onChanged: (value) => setState(() => _serviceRadius = value),
        ),
      ],
    );
  }

  // ── Step 3 — Services ────────────────────────────────────────────────────
  Widget _buildServicesStep() {
    final catalogAsync = ref.watch(serviceCatalogProvider);
    return _StepCard(
      icon: Icons.build_outlined,
      title: '3. Select Services You Provide',
      children: [
        AsyncValueView<List<CatalogCategory>>(
          value: catalogAsync,
          onRetry: () => ref.invalidate(serviceCatalogProvider),
          builder: (context, categories) {
            if (categories.isEmpty) {
              return const Padding(
                padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
                child: Text('No services are currently available in the catalog.'),
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: categories.map((category) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(category.name, style: AppTypography.sectionTitle),
                      const Divider(height: 12),
                      ...category.services.map((service) {
                        final selected = _selectedServices.containsKey(service.id);
                        return CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          dense: true,
                          controlAffinity: ListTileControlAffinity.leading,
                          title: Text(service.name, style: AppTypography.body),
                          value: selected,
                          onChanged: (checked) {
                            setState(() {
                              if (checked ?? false) {
                                _selectedServices[service.id] = {
                                  'id': service.id,
                                  'name': service.name,
                                  'category': service.categoryName ?? category.name,
                                };
                              } else {
                                _selectedServices.remove(service.id);
                              }
                            });
                          },
                        );
                      }),
                    ],
                  ),
                );
              }).toList(),
            );
          },
        ),
      ],
    );
  }

  // ── Step 4 — Skills & Tools ──────────────────────────────────────────────
  Widget _buildSkillsStep() {
    return _StepCard(
      icon: Icons.military_tech_outlined,
      title: '4. Professional Experience & Equipment',
      children: [
        _FieldLabel('Years of Experience', required: false),
        const SizedBox(height: 6),
        TextField(
          controller: _experienceYearsController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: _inputDecoration(hintText: '0–40', icon: Icons.timeline_outlined),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Vehicle Type', required: false),
        const SizedBox(height: 6),
        DropdownButtonFormField<String>(
          initialValue: _vehicleType,
          decoration: _inputDecoration(hintText: 'Select vehicle type', icon: Icons.two_wheeler_outlined),
          items: const [
            DropdownMenuItem(value: 'two_wheeler', child: Text('Two Wheeler')),
            DropdownMenuItem(value: 'four_wheeler', child: Text('Four Wheeler')),
            DropdownMenuItem(value: 'bicycle', child: Text('Bicycle')),
            DropdownMenuItem(value: 'public_transit', child: Text('Public Transit')),
          ],
          onChanged: (value) => setState(() => _vehicleType = value),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Driving License Number', required: false),
        const SizedBox(height: 6),
        TextField(
          controller: _licenseNumberController,
          decoration: _inputDecoration(hintText: 'e.g. DL-0420110012345', icon: Icons.badge_outlined),
        ),
      ],
    );
  }

  // ── Step 5 — Documents ───────────────────────────────────────────────────
  Widget _buildDocumentsStep(EmployeeProfile profile) {
    final byCategory = {for (final d in profile.documents) d.category: d};

    return _StepCard(
      icon: Icons.file_present_outlined,
      title: '5. Required Verification Documents',
      children: _requiredDocuments.map((entry) {
        final (category, title, required) = entry;
        final doc = byCategory[category];
        final uploaded = doc != null && doc.hasFile;

        return Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: uploaded ? AppColors.success.tint : AppColors.surface,
            border: Border.all(color: uploaded ? AppColors.success.tintBorder : AppColors.border),
            borderRadius: BorderRadius.circular(AppRadius.cardStandard),
          ),
          child: Row(
            children: [
              Icon(
                uploaded ? Icons.check_circle_rounded : Icons.upload_file_outlined,
                color: uploaded ? AppColors.success.base : AppColors.textMuted,
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTypography.cardTitle,
                    ),
                    Text(
                      uploaded
                          ? 'Uploaded (${doc.status})'
                          : (required ? 'Required' : 'Optional'),
                      style: AppTypography.metadata,
                    ),
                  ],
                ),
              ),
              OutlinedButton(
                onPressed: () => _handleDocumentUpload(category, title),
                child: Text(uploaded ? 'Replace' : 'Upload'),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Future<void> _handleDocumentUpload(String category, String title) async {
    final picker = ImagePicker();
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: AppSpacing.sm),
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: Text('Take Photo of $title'),
              onTap: () => Navigator.of(context).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from Gallery'),
              onTap: () => Navigator.of(context).pop(ImageSource.gallery),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
    );
    if (source == null) return;

    final image = await picker.pickImage(source: source, imageQuality: 85, maxWidth: 1600);
    if (image == null) return;

    final success = await ref.read(documentsControllerProvider.notifier).uploadDocument(
          category: category,
          filePath: image.path,
          title: title,
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? '$title uploaded.' : 'Failed to upload $title.'),
        backgroundColor: success ? AppColors.success.base : AppColors.error.base,
      ),
    );
  }

  // ── Step 6 — Bank Details ────────────────────────────────────────────────
  Widget _buildBankStep() {
    return _StepCard(
      icon: Icons.account_balance_outlined,
      title: '6. Direct Deposit & Bank Information',
      children: [
        _FieldLabel('Account Holder Name', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _accountHolderController,
          decoration: _inputDecoration(
            hintText: 'As printed on bank passbook',
            icon: Icons.person_outline,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('IFSC Code', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _ifscController,
          textCapitalization: TextCapitalization.characters,
          onChanged: (value) {
            final upper = value.toUpperCase();
            if (upper != value) {
              _ifscController.value = _ifscController.value.copyWith(
                text: upper,
                selection: TextSelection.collapsed(offset: upper.length),
              );
            }
          },
          decoration: _inputDecoration(hintText: 'e.g. HDFC0001234', icon: Icons.numbers_outlined),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Account Number', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _accountNumberController,
          obscureText: _obscureAccountNumber,
          keyboardType: TextInputType.number,
          decoration: _inputDecoration(
            hintText: '••••••••••••',
            icon: Icons.credit_card_outlined,
            suffixIcon: IconButton(
              icon: Icon(_obscureAccountNumber ? Icons.visibility_outlined : Icons.visibility_off_outlined),
              onPressed: () => setState(() => _obscureAccountNumber = !_obscureAccountNumber),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _FieldLabel('Confirm Account Number', required: true),
        const SizedBox(height: 6),
        TextField(
          controller: _confirmAccountNumberController,
          keyboardType: TextInputType.number,
          decoration: _inputDecoration(hintText: 'Re-enter account number', icon: Icons.credit_card_outlined),
        ),
      ],
    );
  }

  // ── Step 7 — Review & Submit ─────────────────────────────────────────────
  Widget _buildReviewStep(EmployeeProfile profile) {
    return _StepCard(
      icon: Icons.checklist_rounded,
      title: '7. Review & Submit Application',
      children: [
        _ReviewRow('City', _cityController.text.isEmpty ? '—' : _cityController.text),
        _ReviewRow('Service Radius', '${_serviceRadius.round()} km'),
        _ReviewRow(
          'Services Selected',
          _selectedServices.isEmpty
              ? '—'
              : _selectedServices.values.map((s) => s['name']).join(', '),
        ),
        _ReviewRow(
          'Experience',
          _experienceYearsController.text.isEmpty
              ? '—'
              : '${_experienceYearsController.text} years',
        ),
        _ReviewRow('Documents Uploaded', '${profile.documents.where((d) => d.hasFile).length}'),
        const SizedBox(height: AppSpacing.lg),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _declarationAccepted,
          onChanged: (value) => setState(() => _declarationAccepted = value ?? false),
          title: const Text(
            'I declare that the information provided is accurate and complete to the best of my knowledge.',
            style: TextStyle(fontSize: 13),
          ),
        ),
      ],
    );
  }

  InputDecoration _inputDecoration({
    required String hintText,
    required IconData icon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      prefixIcon: Icon(icon, color: AppColors.textMuted, size: 18),
      suffixIcon: suffixIcon,
      hintText: hintText,
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.primary, width: 1.5),
      ),
    );
  }
}

class _WizardProgressHeader extends StatelessWidget {
  const _WizardProgressHeader({required this.currentStep});

  final int currentStep;

  @override
  Widget build(BuildContext context) {
    final percent = (currentStep / 7 * 100).round();
    return Container(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Step $currentStep of 7: ${_stepLabels[currentStep - 1]}',
                style: AppTypography.cardTitle,
              ),
              Text('$percent% Complete', style: AppTypography.metadata),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: currentStep / 7,
              minHeight: 6,
              backgroundColor: AppColors.surfaceMuted,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.success.base),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 28,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _stepLabels.length,
              separatorBuilder: (context, index) => const SizedBox(width: 6),
              itemBuilder: (context, index) {
                final stepNumber = index + 1;
                final isDone = stepNumber < currentStep;
                final isCurrent = stepNumber == currentStep;
                final color = isDone
                    ? AppColors.success.base
                    : (isCurrent ? AppColors.primary : AppColors.textMuted);
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: isCurrent ? AppColors.info.tint : Colors.transparent,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: color.withValues(alpha: isCurrent ? 1 : 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isDone ? Icons.check_circle_rounded : Icons.circle_outlined,
                        size: 13,
                        color: color,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '$stepNumber',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _WizardFooter extends StatelessWidget {
  const _WizardFooter({
    required this.currentStep,
    required this.isSaving,
    required this.canSubmit,
    required this.onBack,
    required this.onNext,
    required this.onSubmit,
  });

  final int currentStep;
  final bool isSaving;
  final bool canSubmit;
  final VoidCallback? onBack;
  final VoidCallback? onNext;
  final VoidCallback? onSubmit;

  @override
  Widget build(BuildContext context) {
    final isLastStep = currentStep == 7;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          if (currentStep > 1)
            Expanded(
              child: OutlinedButton(
                onPressed: onBack,
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                child: const Text('Back'),
              ),
            ),
          if (currentStep > 1) const SizedBox(width: AppSpacing.md),
          Expanded(
            flex: 2,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [AppColors.primary, AppColors.success.base]),
                borderRadius: BorderRadius.circular(AppRadius.button),
              ),
              child: ElevatedButton(
                onPressed: isLastStep ? (canSubmit ? onSubmit : null) : onNext,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  disabledBackgroundColor: Colors.transparent,
                  foregroundColor: Colors.white,
                  disabledForegroundColor: Colors.white70,
                  shadowColor: Colors.transparent,
                  elevation: 0,
                  minimumSize: const Size.fromHeight(48),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.button)),
                ),
                child: isSaving
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Text(
                        isLastStep ? 'Submit Application' : 'Save & Continue',
                        style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({required this.icon, required this.title, required this.children});

  final IconData icon;
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.primary, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: AppTypography.sectionTitle)),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          ...children,
        ],
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.label, {required this.required});

  final String label;
  final bool required;

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        text: label,
        style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
        children: [
          if (required) const TextSpan(text: ' *', style: TextStyle(color: Color(0xFFE11D48))),
        ],
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 130, child: Text(label, style: AppTypography.supporting)),
          Expanded(child: Text(value, style: AppTypography.body)),
        ],
      ),
    );
  }
}
